# Project: Free Bulk Email Verification Web App

Act as a senior Python developer. Build a complete, working email verification web application that I can run locally on my Fedora Linux computer.

## 1. Project Goal

I have a list of email addresses, and I want to determine which addresses are likely to be valid, invalid, or impossible to verify.

Build an application similar in basic functionality to ZeroBounce or Hunter Email Verifier, using free and open-source libraries without requiring paid APIs.

The application must be honest about verification accuracy. Do not claim that an email is active just because its domain exists or its mail server accepts a connection.

## 2. Technology Stack

Use the following technologies:

- Python 3
- Flask for the backend
- HTML5 and CSS3 for the frontend
- JavaScript for interactive functionality
- dnspython for DNS and MX record lookups
- email-validator for email syntax and domain validation
- pandas for CSV and Excel processing
- openpyxl for Excel file support
- Python's built-in socket and SMTP libraries where appropriate

Do not use TypeScript, React, paid APIs, or a database unless genuinely necessary.

The application should run locally on Fedora Linux.

## 3. User Interface

Create a modern, responsive dashboard with the following sections:

### Dashboard
Display summary cards showing:

- Total emails uploaded
- Valid format
- Invalid addresses
- Deliverable candidates
- Risky addresses
- Unknown results
- Duplicate addresses

Use a clean, professional design with readable typography, responsive layouts, and clear status badges.

### Upload Section

Allow users to:

1. Upload a CSV file.
2. Upload an Excel XLSX file.
3. Paste email addresses into a text area.
4. Select the column containing email addresses when a spreadsheet has multiple columns.
5. Remove duplicates automatically or choose to retain them.
6. Preview the first 20 email addresses before starting verification.

Accept files containing thousands of email addresses, subject to reasonable configurable limits.

Validate uploaded files and reject unsupported formats or excessively large files with understandable error messages.

### Verification Section

Include:

- Start Verification button
- Pause button, if safely implementable
- Cancel button
- Progress bar
- Number of processed addresses
- Number of remaining addresses
- Current verification status

Do not freeze the web interface during verification.

Use background processing and a progress endpoint, or another simple and reliable architecture. Do not add Celery or Redis unless necessary.

## 4. Email Verification Engine

Implement verification as separate, reusable Python functions.

### Check A: Syntax Validation

Check whether an email address follows valid email syntax.

Use the email-validator library.

Return:
- VALID_FORMAT
- INVALID_FORMAT

Do not treat syntax validity as proof that a mailbox exists.

### Check B: Domain and DNS Validation

Check whether the domain exists and whether it has usable mail-routing records.

Use dnspython to look up MX records.

Handle:
- Valid MX records
- Missing MX records
- DNS timeouts
- NXDOMAIN responses
- Temporary DNS errors
- Domains that may receive email through implicit MX behavior

Do not automatically classify every domain without an MX record as invalid. Consider whether an A or AAAA record allows implicit mail delivery, and explain the limitations in the result.

### Check C: Disposable Email Detection

Implement a local, optional disposable-email domain blocklist.

Allow the user to add or update domains in a local text file.

Do not require an external paid service.

If no reliable classification is available, return UNKNOWN rather than guessing.

### Check D: Role-Based Address Detection

Identify common role-based addresses, including:

- info@
- support@
- sales@
- admin@
- contact@
- help@
- billing@
- noreply@

Return a separate flag called ROLE_BASED.

A role-based address is not automatically invalid.

### Check E: Catch-All Detection

Where technically appropriate, optionally attempt to identify catch-all mail servers.

A catch-all domain may accept mail for nonexistent recipients.

Never claim that catch-all detection proves a mailbox exists.

If the result cannot be determined reliably, use UNKNOWN.

### Check F: SMTP Verification

Implement an optional SMTP verification module.

Requirements:

- Use configurable connection timeouts.
- Handle connection failures, rate limits, DNS errors, and SMTP response codes.
- Do not send an actual email during mailbox verification.
- Do not send message bodies or spam.
- Respect provider restrictions and stop retrying when a server refuses verification attempts.
- Do not repeatedly probe the same domain.
- Use conservative concurrency and configurable rate limits.
- Never interpret a timeout, connection refusal, or anti-abuse response as proof that an address is invalid.
- Do not attempt to bypass CAPTCHA, authentication, rate limits, or provider security controls.
- Do not perform SMTP VRFY commands as if they were reliable mailbox checks.
- Make SMTP verification optional because many providers block or obscure recipient verification.
- Provide a configuration option to disable SMTP verification entirely.

Interpret SMTP responses conservatively:

- An explicit recipient rejection may indicate an invalid address, but only when the response is sufficiently clear.
- A temporary failure must return UNKNOWN or TEMPORARY_ERROR.
- A successful recipient acceptance means only that the server accepted the recipient during this test.
- An acceptance response does not guarantee that the mailbox exists, is monitored, or can receive mail in the future.

Do not claim that the app can reliably confirm every Gmail or Microsoft mailbox.

## 5. Final Status Classification

Use the following final statuses:

### INVALID
Use only when there is sufficiently strong evidence of invalidity, such as clearly invalid syntax or a confirmed nonexistent domain.

### LIKELY_VALID
Use when the address has valid syntax, the domain has plausible mail-routing configuration, and no strong evidence of invalidity was found.

This status must not be described as proof of an active mailbox.

### ACCEPTED_BY_SERVER
Use when an optional SMTP check receives a recipient-acceptance response.

Clearly explain that acceptance is not proof of mailbox existence.

### RISKY
Use for conditions such as:
- Disposable email domain
- Catch-all domain
- Other explicitly identified delivery risks

Keep the underlying reasons available in the results.

### UNKNOWN
Use when the application cannot determine the status confidently.

Examples:
- SMTP verification blocked
- Verification timeout
- Inconclusive server response
- DNS temporarily unavailable

Do not label every inconclusive address invalid.

### ROLE_BASED
Store this as a separate flag rather than treating it as a final validity status.

Use an additional verification_reason field to explain every result.

## 6. Results Table

Display a searchable, sortable table with:

- Email address
- Syntax status
- Domain status
- MX status
- Disposable status
- Role-based flag
- SMTP result
- Final status
- Verification reason

Allow filtering by:
- All
- Likely valid
- Invalid
- Accepted by server
- Risky
- Unknown
- Role-based

Use clear colors for the status badges.

Add pagination so large result sets do not overload the browser.

## 7. Export Results

Allow the user to download results as:

- CSV
- Excel XLSX

Include all verification results and reasons.

Also provide separate exports for:

- Likely-valid addresses
- Invalid addresses
- Risky addresses
- Unknown addresses

Ensure that the original email address is preserved in the exported report.

## 8. Performance and Reliability

The application should:

- Support thousands of email addresses.
- Avoid querying DNS repeatedly for the same domain.
- Cache DNS results for an appropriate period.
- Apply configurable concurrency limits.
- Use reasonable network timeouts.
- Handle exceptions without crashing the entire job.
- Keep verification progress accurate.
- Avoid excessive requests to any one mail server.
- Stop cleanly when a user cancels a job.
- Avoid storing uploaded email lists permanently unless the user explicitly chooses to save them.

Do not use aggressive SMTP probing or claim that high concurrency guarantees better verification.

For very large lists, process addresses in batches and make the limits configurable.

## 9. Privacy and Security

This application will process potentially sensitive business email lists.

Implement the following:

- Bind the Flask development server to 127.0.0.1 by default.
- Set reasonable upload size limits.
- Validate uploaded filenames and file types.
- Never execute uploaded files.
- Prevent path traversal.
- Do not log full email addresses unnecessarily.
- Keep temporary files in a dedicated directory.
- Delete temporary uploads and exports when appropriate.
- Do not send email lists to external verification services.
- Do not expose the application publicly without appropriate authentication and security hardening.

DNS lookups and optional SMTP checks will necessarily contact external infrastructure for the domains being verified. Explain this in the README.

## 10. Recommended Project Structure

Create this structure:

email-verifier/
├── app.py
├── verifier.py
├── config.py
├── requirements.txt
├── README.md
├── data/
│   └── disposable_domains.txt
├── templates/
│   └── index.html
├── static/
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── app.js
├── uploads/
└── exports/

You may improve the structure if there is a clear technical reason.

Do not commit uploaded email lists, exports, or other private data to Git.

## 11. Testing

Include tests for:

- Valid email syntax
- Invalid email syntax
- Missing MX records
- Nonexistent domains
- DNS timeouts
- Disposable domains
- Role-based addresses
- SMTP timeouts
- SMTP recipient rejection
- SMTP recipient acceptance
- Temporary SMTP failures
- Duplicate removal
- CSV uploads
- XLSX uploads
- CSV exports
- XLSX exports
- Cancellation and progress reporting

Mock external DNS and SMTP responses in unit tests so the test suite can run without probing real email servers.

## 12. README and Installation

Write a complete README with beginner-friendly instructions for Fedora Linux.

Include commands to:

1. Install Python and pip if needed.
2. Create the project directory.
3. Create a Python virtual environment.
4. Activate the environment.
5. Install dependencies.
6. Run the Flask application.
7. Open the application in a browser.
8. Upload an email list.
9. Verify the results.
10. Export the report.
11. Troubleshoot common errors.

Keep terminal commands short and easy to follow.

Provide a requirements.txt file with all necessary dependencies.

## 13. Development Instructions

First inspect the existing project directory so you do not overwrite unrelated files.

Then implement the complete application, including all Python files, HTML, CSS, JavaScript, configuration, tests, and documentation.

Do not provide pseudocode or empty placeholder functions.

Make the code runnable and ensure all imports and endpoint names are consistent.

Run the available tests and fix any errors you find.

If a feature cannot be implemented reliably without a paid service or cooperation from the recipient's email provider, implement the best honest alternative and document the limitation.

At the end, provide:
- A summary of the completed features
- The project file structure
- Exact installation commands
- The command to start the application
- The local URL
- Any remaining limitations

The final application must be genuinely usable, not merely a UI mockup.