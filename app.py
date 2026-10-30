from __future__ import annotations

import csv
import io
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd
from flask import Flask, jsonify, render_template, request, send_file
from werkzeug.utils import secure_filename

import config
from verifier import load_disposable_domains, verify_email

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = config.MAX_UPLOAD_BYTES
jobs: dict[str, dict] = {}
jobs_lock = threading.Lock()


def parse_emails_from_request() -> list[str]:
    pasted = request.form.get("emails", "")
    values = [line.strip() for line in pasted.replace(",", "\n").splitlines() if line.strip()]
    upload = request.files.get("file")
    if upload and upload.filename:
        filename = secure_filename(upload.filename)
        suffix = Path(filename).suffix.lower()
        if suffix not in {".csv", ".xlsx"}:
            raise ValueError("Only CSV and XLSX files are supported")
        data = upload.read()
        if suffix == ".csv":
            frame = pd.read_csv(io.BytesIO(data), dtype=str)
        else:
            frame = pd.read_excel(io.BytesIO(data), dtype=str)
        if frame.empty:
            raise ValueError("The uploaded file is empty")
        column = request.form.get("column") or str(frame.columns[0])
        if column not in frame.columns:
            raise ValueError("The selected email column was not found")
        values.extend(str(value).strip() for value in frame[column].dropna() if str(value).strip())
    if not values:
        raise ValueError("Paste email addresses or upload a CSV/XLSX file")
    if len(values) > config.MAX_EMAILS:
        raise ValueError(f"Too many addresses; the limit is {config.MAX_EMAILS}")
    return values


def run_job(job_id: str, emails: list[str], smtp_enabled: bool) -> None:
    disposable = load_disposable_domains(config.DISPOSABLE_FILE)
    results = []
    with ThreadPoolExecutor(max_workers=config.MAX_WORKERS) as pool:
        futures = [pool.submit(verify_email, email, disposable, config.DNS_TIMEOUT, smtp_enabled, config.SMTP_TIMEOUT) for email in emails]
        for future in futures:
            with jobs_lock:
                job = jobs[job_id]
                if job["cancelled"]:
                    break
                while job["paused"] and not job["cancelled"]:
                    jobs_lock.release()
                    threading.Event().wait(0.1)
                    jobs_lock.acquire()
                if job["cancelled"]:
                    break
            result = future.result()
            results.append(result.as_dict())
            with jobs_lock:
                jobs[job_id]["processed"] = len(results)
                jobs[job_id]["results"] = results
    with jobs_lock:
        jobs[job_id]["status"] = "CANCELLED" if jobs[job_id]["cancelled"] else "COMPLETE"


def export_rows(rows: list[dict], suffix: str):
    frame = pd.DataFrame(rows)
    if suffix == "csv":
        stream = io.BytesIO(frame.to_csv(index=False).encode("utf-8"))
        return send_file(stream, mimetype="text/csv", as_attachment=True, download_name="email-results.csv")
    stream = io.BytesIO()
    with pd.ExcelWriter(stream, engine="openpyxl") as writer:
        frame.to_excel(writer, index=False, sheet_name="Results")
    stream.seek(0)
    return send_file(stream, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", as_attachment=True, download_name="email-results.xlsx")


def export_simple_rows(rows: list[dict], filename: str):
    frame = pd.DataFrame(
        [{"email": row["email"], "verified": row["verified"]} for row in rows],
        columns=["email", "verified"],
    )
    stream = io.BytesIO(frame.to_csv(index=False).encode("utf-8"))
    return send_file(stream, mimetype="text/csv", as_attachment=True, download_name=filename)


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/api/preview")
def preview():
    try:
        emails = parse_emails_from_request()
        unique = list(dict.fromkeys(emails))
        return jsonify({"emails": unique[:20], "total": len(emails), "duplicates": len(emails) - len(unique)})
    except (ValueError, pd.errors.ParserError) as exc:
        return jsonify({"error": str(exc)}), 400


@app.post("/api/jobs")
def create_job():
    try:
        emails = parse_emails_from_request()
    except (ValueError, pd.errors.ParserError) as exc:
        return jsonify({"error": str(exc)}), 400
    if request.form.get("keep_duplicates") != "true":
        emails = list(dict.fromkeys(emails))
    job_id = uuid.uuid4().hex
    with jobs_lock:
        jobs[job_id] = {"status": "RUNNING", "total": len(emails), "processed": 0, "results": [], "paused": False, "cancelled": False}
    smtp_requested = request.form.get("smtp") == "true"
    threading.Thread(target=run_job, args=(job_id, emails, smtp_requested and config.SMTP_ENABLED), daemon=True).start()
    return jsonify({"job_id": job_id})


@app.get("/api/jobs/<job_id>")
def job_status(job_id: str):
    with jobs_lock:
        job = jobs.get(job_id)
        if not job:
            return jsonify({"error": "Job not found"}), 404
        return jsonify(job)


@app.post("/api/jobs/<job_id>/<action>")
def job_action(job_id: str, action: str):
    if action not in {"pause", "resume", "cancel"}:
        return jsonify({"error": "Unsupported action"}), 400
    with jobs_lock:
        if job_id not in jobs:
            return jsonify({"error": "Job not found"}), 404
        if action == "pause":
            jobs[job_id]["paused"] = True
        elif action == "resume":
            jobs[job_id]["paused"] = False
        else:
            jobs[job_id]["cancelled"] = True
    return jsonify({"ok": True})


@app.post("/api/export/<job_id>")
def export_job(job_id: str):
    with jobs_lock:
        job = jobs.get(job_id)
        if not job:
            return jsonify({"error": "Job not found"}), 404
        rows = job["results"]
    requested_status = request.form.get("status")
    if requested_status:
        rows = [row for row in rows if row["final_status"] == requested_status]
    return export_rows(rows, request.form.get("format", "csv"))


@app.post("/api/export/<job_id>/<category>")
def export_category(job_id: str, category: str):
    if category not in {"valid", "invalid"}:
        return jsonify({"error": "Unsupported export category"}), 400
    with jobs_lock:
        job = jobs.get(job_id)
        if not job:
            return jsonify({"error": "Job not found"}), 404
        rows = job["results"]
    if category == "valid":
        rows = [row for row in rows if row["final_status"] in {"LIKELY_VALID", "ACCEPTED_BY_SERVER"}]
        rows = [{"email": row["email"], "verified": True} for row in rows]
        return export_simple_rows(rows, "valid-emails.csv")
    rows = [row for row in rows if row["final_status"] == "INVALID"]
    rows = [{"email": row["email"], "verified": False} for row in rows]
    return export_simple_rows(rows, "invalid-emails.csv")


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
