from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
EXPORT_DIR = BASE_DIR / "exports"
DISPOSABLE_FILE = BASE_DIR / "data" / "disposable_domains.txt"
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", str(10 * 1024 * 1024)))
MAX_EMAILS = int(os.getenv("MAX_EMAILS", "10000"))
DNS_TIMEOUT = float(os.getenv("DNS_TIMEOUT", "5"))
SMTP_TIMEOUT = float(os.getenv("SMTP_TIMEOUT", "8"))
MAX_WORKERS = int(os.getenv("MAX_WORKERS", "8"))
SMTP_ENABLED = os.getenv("SMTP_ENABLED", "true").lower() == "true"

for directory in (UPLOAD_DIR, EXPORT_DIR, DISPOSABLE_FILE.parent):
    directory.mkdir(parents=True, exist_ok=True)
