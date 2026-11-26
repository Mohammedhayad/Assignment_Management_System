# BMSIT CSE Assignment Management System

A Flask, SQLite, and vanilla JavaScript assignment portal based on the provided SRS and system test plan. The initial release implements secure sign-in, role-specific dashboards, assignment drafts and publication, class/subject visibility, private file submissions, grading, result publication, in-app notifications, and basic administrator account management.

## Run locally

```powershell
cd C:\AMSystem\AMS
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:5000`. The app creates its SQLite database and private upload directory under Flask's `instance` folder on first run. Set a persistent `SECRET_KEY` environment variable before deploying; configure HTTPS, backup/restore, upload limits, allowed file types, and the department-approved late/resubmission policies for production.

## Demo accounts

| Role | Email | Password |
| --- | --- | --- |
| Student | `student@bmsit.edu` | `Student123!` |
| Professor | `professor@bmsit.edu` | `Professor123!` |
| Administrator | `admin@bmsit.edu` | `Admin123!` |

These are development-only accounts. Change/remove them and provision real accounts securely before deployment. `student2@bmsit.edu` and `student-b@bmsit.edu` are also seeded to exercise class-level isolation.

## Policies and storage

The prototype accepts late submissions and permits resubmission by default; change `LATE_SUBMISSIONS` and `RESUBMISSIONS_ENABLED` in `create_app` to test other policies. Uploads are limited to 10 MB and candidate formats PDF, DOCX, PPTX, and ZIP. File names are generated on the server and files are served only through authorization-checked routes. DOCX and PPTX uploads are checked for their expected ZIP package contents.

The seeded professor is mapped to four CSE subjects in Semester 3, Section A. Student visibility is constrained by those subject/class mappings. SQLite and local disk are intended for a prototype or small deployment, not high-concurrency production use.

## Test

```powershell
python -m unittest discover -s tests -v
```
