import os
import secrets
import sqlite3
import uuid
import zipfile
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from functools import wraps
from io import BytesIO
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_from_directory, session
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename


IST = timezone(timedelta(hours=5, minutes=30), "IST")
ALLOWED_EXTENSIONS = {"pdf", "docx", "pptx", "zip"}
SUBJECTS = ("Data Structures", "Database Systems", "Web Technology", "Operating Systems")


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY") or secrets.token_hex(32),
        DATABASE=str(Path(app.instance_path) / "ams.sqlite3"),
        UPLOAD_FOLDER=str(Path(app.instance_path) / "uploads"),
        MAX_CONTENT_LENGTH=10 * 1024 * 1024,
        LATE_SUBMISSIONS="accept",
        RESUBMISSIONS_ENABLED=True,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
    )
    if test_config:
        app.config.update(test_config)
    Path(app.config["DATABASE"]).parent.mkdir(parents=True, exist_ok=True)
    Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)

    @contextmanager
    def connect_db():
        connection = sqlite3.connect(app.config["DATABASE"])
        try:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            with connection:
                yield connection
        finally:
            connection.close()

    def initialize_db():
        with connect_db() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('student','professor','admin')),
                    active INTEGER NOT NULL DEFAULT 1,
                    usn TEXT,
                    semester INTEGER,
                    section TEXT,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS user_subjects (
                    user_id INTEGER NOT NULL REFERENCES users(id),
                    subject TEXT NOT NULL,
                    semester INTEGER NOT NULL,
                    section TEXT NOT NULL,
                    PRIMARY KEY(user_id, subject, semester, section)
                );
                CREATE TABLE IF NOT EXISTS assignments (
                    id INTEGER PRIMARY KEY,
                    professor_id INTEGER NOT NULL REFERENCES users(id),
                    subject TEXT NOT NULL,
                    semester INTEGER NOT NULL,
                    section TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    due_at TEXT NOT NULL,
                    max_marks REAL NOT NULL CHECK(max_marks > 0),
                    status TEXT NOT NULL CHECK(status IN ('draft','published','closed')),
                    created_at TEXT NOT NULL,
                    allow_resubmissions INTEGER NOT NULL DEFAULT 1
                );
                CREATE TABLE IF NOT EXISTS submissions (
                    id INTEGER PRIMARY KEY,
                    assignment_id INTEGER NOT NULL REFERENCES assignments(id),
                    student_id INTEGER NOT NULL REFERENCES users(id),
                    version INTEGER NOT NULL,
                    stored_name TEXT NOT NULL,
                    original_name TEXT NOT NULL,
                    mime_type TEXT NOT NULL,
                    size INTEGER NOT NULL,
                    submitted_at TEXT NOT NULL,
                    status TEXT NOT NULL,
                    UNIQUE(assignment_id, student_id, version)
                );
                CREATE TABLE IF NOT EXISTS grades (
                    id INTEGER PRIMARY KEY,
                    submission_id INTEGER NOT NULL UNIQUE REFERENCES submissions(id),
                    marks REAL NOT NULL,
                    feedback TEXT NOT NULL DEFAULT '',
                    graded_by INTEGER NOT NULL REFERENCES users(id),
                    graded_at TEXT NOT NULL,
                    published_at TEXT
                );
                CREATE TABLE IF NOT EXISTS notifications (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id),
                    title TEXT NOT NULL,
                    message TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    is_read INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS audit_events (
                    id INTEGER PRIMARY KEY,
                    actor_id INTEGER NOT NULL REFERENCES users(id),
                    action TEXT NOT NULL,
                    target_type TEXT NOT NULL,
                    target_id INTEGER NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )
            if db.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
                now = now_ist()
                demo_users = [
                    ("Aarav Sharma", "student@bmsit.edu", "Student123!", "student", "1BM23CS001", 3, "A"),
                    ("Diya Rao", "student2@bmsit.edu", "Student123!", "student", "1BM23CS002", 3, "A"),
                    ("Kabir Nair", "student-b@bmsit.edu", "Student123!", "student", "1BM23CS003", 3, "B"),
                    ("Prof. Ananya Rao", "professor@bmsit.edu", "Professor123!", "professor", None, None, None),
                    ("System Admin", "admin@bmsit.edu", "Admin123!", "admin", None, None, None),
                ]
                for name, email, password, role, usn, semester, section in demo_users:
                    db.execute(
                        """INSERT INTO users(name,email,password_hash,role,usn,semester,section,created_at)
                           VALUES(?,?,?,?,?,?,?,?)""",
                        (name, email, generate_password_hash(password), role, usn, semester, section, now),
                    )
                professor_id = db.execute(
                    "SELECT id FROM users WHERE email='professor@bmsit.edu'"
                ).fetchone()["id"]
                for subject in SUBJECTS:
                    db.execute(
                        "INSERT INTO user_subjects(user_id,subject,semester,section) VALUES(?,?,3,'A')",
                        (professor_id, subject),
                    )
                for student_email, subjects in (
                    ("student@bmsit.edu", SUBJECTS),
                    ("student2@bmsit.edu", SUBJECTS),
                    ("student-b@bmsit.edu", SUBJECTS),
                ):
                    student_id = db.execute("SELECT id FROM users WHERE email=?", (student_email,)).fetchone()["id"]
                    student = db.execute("SELECT semester,section FROM users WHERE id=?", (student_id,)).fetchone()
                    for subject in subjects:
                        db.execute(
                            "INSERT INTO user_subjects(user_id,subject,semester,section) VALUES(?,?,?,?)",
                            (student_id, subject, student["semester"], student["section"]),
                        )
                db.execute(
                    """INSERT INTO assignments
                       (professor_id,subject,semester,section,title,description,due_at,max_marks,status,created_at)
                       VALUES(?,?,?,?,?,?,?,?,?,?)""",
                    (
                        professor_id,
                        "Data Structures",
                        3,
                        "A",
                        "Graph Algorithms",
                        "Implement and analyze breadth-first search and depth-first search. Submit your source code and a short explanation.",
                        (datetime.now(IST).replace(hour=23, minute=59, second=0, microsecond=0)).isoformat(),
                        20,
                        "published",
                        now,
                    ),
                )
                assignment_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
                notify_students(db, assignment_id, "New assignment", "Graph Algorithms is now available.")

    def now_ist():
        return datetime.now(IST).isoformat(timespec="seconds")

    def notify_students(db, assignment_id, title, message):
        target = db.execute("SELECT subject,semester,section FROM assignments WHERE id=?", (assignment_id,)).fetchone()
        students = db.execute(
            """SELECT DISTINCT u.id FROM users u JOIN user_subjects us ON us.user_id=u.id
               WHERE u.role='student' AND u.active=1 AND us.subject=? AND us.semester=? AND us.section=?""",
            (target["subject"], target["semester"], target["section"]),
        ).fetchall()
        for student in students:
            db.execute(
                "INSERT INTO notifications(user_id,title,message,created_at) VALUES(?,?,?,?)",
                (student["id"], title, message, now_ist()),
            )

    initialize_db()

    def api_error(message, status):
        return jsonify({"error": message}), status

    def current_user():
        user_id = session.get("user_id")
        if not user_id:
            return None
        with connect_db() as db:
            user = db.execute(
                "SELECT id,name,email,role,active,usn,semester,section FROM users WHERE id=?",
                (user_id,),
            ).fetchone()
            return dict(user) if user and user["active"] else None

    def require_role(*roles):
        def decorator(view):
            @wraps(view)
            def wrapped(*args, **kwargs):
                user = current_user()
                if user is None:
                    return api_error("Authentication required.", 401)
                if user["role"] not in roles:
                    return api_error("You do not have permission to perform this action.", 403)
                if request.method not in ("GET", "HEAD", "OPTIONS"):
                    token = request.headers.get("X-CSRF-Token")
                    if not token or not secrets.compare_digest(token, session.get("csrf_token", "")):
                        return api_error("Invalid or missing CSRF token.", 400)
                return view(user, *args, **kwargs)
            return wrapped
        return decorator

    def professor_owns(db, user_id, assignment_id):
        return db.execute(
            "SELECT 1 FROM assignments WHERE id=? AND professor_id=?",
            (assignment_id, user_id),
        ).fetchone() is not None

    def student_can_see(db, user_id, assignment_id):
        return db.execute(
            """SELECT 1 FROM assignments a JOIN user_subjects us
               ON us.subject=a.subject AND us.semester=a.semester AND us.section=a.section
               WHERE a.id=? AND a.status='published' AND us.user_id=?""",
            (assignment_id, user_id),
        ).fetchone() is not None

    def assignment_json(row):
        return {
            "id": row["id"],
            "subject": row["subject"],
            "semester": row["semester"],
            "section": row["section"],
            "title": row["title"],
            "description": row["description"],
            "due_at": row["due_at"],
            "max_marks": row["max_marks"],
            "status": row["status"],
            "professor": row["professor"],
            "submission_id": row["submission_id"],
            "submission_status": row["submission_status"],
            "submitted_at": row["submitted_at"],
            "marks": row["marks"] if row["published_at"] else None,
            "feedback": row["feedback"] if row["published_at"] else None,
            "result_published": bool(row["published_at"]),
        }

    def assignment_query(where, params):
        return f"""SELECT a.*, p.name AS professor,
                       s.id AS submission_id,s.status AS submission_status,s.submitted_at,
                       g.marks,g.feedback,g.published_at
                    FROM assignments a JOIN users p ON p.id=a.professor_id
                    LEFT JOIN submissions s ON s.id=(
                       SELECT MAX(s2.id) FROM submissions s2
                       WHERE s2.assignment_id=a.id AND s2.student_id=?
                    )
                    LEFT JOIN grades g ON g.submission_id=s.id
                    WHERE {where} ORDER BY a.due_at"""

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.errorhandler(413)
    def request_too_large(_error):
        return api_error("Upload exceeds the configured 10 MB limit.", 413)

    @app.post("/api/auth/login")
    def login():
        data = request.get_json(silent=True) or {}
        email = str(data.get("email", "")).strip().lower()
        password = str(data.get("password", ""))
        with connect_db() as db:
            user = db.execute("SELECT * FROM users WHERE email=? AND active=1", (email,)).fetchone()
            if not user or not check_password_hash(user["password_hash"], password):
                return api_error("Email or password is incorrect.", 401)
            session.clear()
            session["user_id"] = user["id"]
            session["csrf_token"] = secrets.token_urlsafe(32)
            return jsonify(
                {
                    "user": {
                        "id": user["id"],
                        "name": user["name"],
                        "email": user["email"],
                        "role": user["role"],
                        "semester": user["semester"],
                        "section": user["section"],
                    },
                    "csrf_token": session["csrf_token"],
                }
            )

    @app.post("/api/auth/logout")
    @require_role("student", "professor", "admin")
    def logout(_user):
        session.clear()
        return jsonify({"message": "Signed out."})

    @app.get("/api/me")
    @require_role("student", "professor", "admin")
    def me(user):
        return jsonify({"user": user, "csrf_token": session.get("csrf_token")})

    @app.get("/api/student/assignments")
    @require_role("student")
    def student_assignments(user):
        with connect_db() as db:
            rows = db.execute(
                assignment_query(
                    """a.status='published' AND EXISTS (
                       SELECT 1 FROM user_subjects us WHERE us.user_id=?
                       AND us.subject=a.subject AND us.semester=a.semester AND us.section=a.section)""",
                    (user["id"], user["id"], user["id"]),
                ),
                (user["id"], user["id"]),
            ).fetchall()
            return jsonify({"assignments": [assignment_json(row) for row in rows]})

    @app.get("/api/assignments/<int:assignment_id>")
    @require_role("student", "professor", "admin")
    def assignment_detail(user, assignment_id):
        with connect_db() as db:
            assignment = db.execute("SELECT * FROM assignments WHERE id=?", (assignment_id,)).fetchone()
            if not assignment:
                return api_error("Assignment not found.", 404)
            if user["role"] == "student" and not student_can_see(db, user["id"], assignment_id):
                return api_error("Assignment not found.", 404)
            if user["role"] == "professor" and not professor_owns(db, user["id"], assignment_id):
                return api_error("Assignment not found.", 404)
            return jsonify({"assignment": dict(assignment)})

    @app.get("/api/professor/assignments")
    @require_role("professor")
    def professor_assignments(user):
        with connect_db() as db:
            rows = db.execute(
                """SELECT a.*,
                       (SELECT COUNT(*) FROM submissions s WHERE s.assignment_id=a.id) AS submission_count,
                       (SELECT COUNT(*) FROM submissions s JOIN grades g ON g.submission_id=s.id
                        WHERE s.assignment_id=a.id AND g.published_at IS NOT NULL) AS reviewed_count
                   FROM assignments a WHERE a.professor_id=? ORDER BY a.due_at""",
                (user["id"],),
            ).fetchall()
            return jsonify({"assignments": [dict(row) for row in rows]})

    @app.post("/api/professor/assignments")
    @require_role("professor")
    def create_assignment(user):
        data = request.get_json(silent=True) or {}
        required = ("subject", "semester", "section", "title", "description", "due_at", "max_marks")
        if any(not str(data.get(field, "")).strip() for field in required):
            return api_error("Subject, class, title, instructions, deadline and maximum marks are required.", 422)
        try:
            semester = int(data["semester"])
            max_marks = float(data["max_marks"])
            due_at = parse_deadline(data["due_at"])
        except (TypeError, ValueError):
            return api_error("Enter a valid semester, deadline and maximum marks.", 422)
        if max_marks <= 0 or max_marks > 1000:
            return api_error("Maximum marks must be greater than zero and at most 1000.", 422)
        subject, section = str(data["subject"]).strip(), str(data["section"]).strip()
        if not (1 <= semester <= 8) or len(section) > 10 or len(str(data["title"])) > 160:
            return api_error("The class or title is invalid.", 422)
        with connect_db() as db:
            mapped = db.execute(
                "SELECT 1 FROM user_subjects WHERE user_id=? AND subject=? AND semester=? AND section=?",
                (user["id"], subject, semester, section),
            ).fetchone()
            if not mapped:
                return api_error("You are not mapped to teach this subject and section.", 403)
            cursor = db.execute(
                """INSERT INTO assignments
                   (professor_id,subject,semester,section,title,description,due_at,max_marks,status,created_at,allow_resubmissions)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    user["id"], subject, semester, section, str(data["title"]).strip(),
                    str(data["description"]).strip(), due_at.isoformat(), max_marks,
                    "draft", now_ist(), int(bool(data.get("allow_resubmissions", app.config["RESUBMISSIONS_ENABLED"]))),
                ),
            )
            assignment_id = cursor.lastrowid
            db.execute(
                "INSERT INTO audit_events(actor_id,action,target_type,target_id,created_at) VALUES(?,?,?,?,?)",
                (user["id"], "assignment_created", "assignment", assignment_id, now_ist()),
            )
            return jsonify({"id": assignment_id, "status": "draft"}), 201

    @app.put("/api/professor/assignments/<int:assignment_id>")
    @require_role("professor")
    def update_assignment(user, assignment_id):
        data = request.get_json(silent=True) or {}
        with connect_db() as db:
            assignment = db.execute("SELECT * FROM assignments WHERE id=?", (assignment_id,)).fetchone()
            if not assignment or assignment["professor_id"] != user["id"]:
                return api_error("Assignment not found.", 404)
            title = str(data.get("title", assignment["title"])).strip()
            description = str(data.get("description", assignment["description"])).strip()
            if not title or not description or len(title) > 160:
                return api_error("A valid title and instructions are required.", 422)
            due_at = assignment["due_at"]
            if "due_at" in data:
                try:
                    due_at = parse_deadline(data["due_at"]).isoformat()
                except (TypeError, ValueError):
                    return api_error("Enter a valid deadline.", 422)
            db.execute(
                "UPDATE assignments SET title=?,description=?,due_at=? WHERE id=?",
                (title, description, due_at, assignment_id),
            )
            return jsonify({"message": "Assignment updated."})

    @app.post("/api/assignments/<int:assignment_id>/publish")
    @require_role("professor")
    def publish_assignment(user, assignment_id):
        with connect_db() as db:
            assignment = db.execute("SELECT * FROM assignments WHERE id=?", (assignment_id,)).fetchone()
            if not assignment or assignment["professor_id"] != user["id"]:
                return api_error("Assignment not found.", 404)
            if assignment["status"] == "closed":
                return api_error("Closed assignments cannot be published.", 409)
            db.execute("UPDATE assignments SET status='published' WHERE id=?", (assignment_id,))
            notify_students(db, assignment_id, "New assignment", f"{assignment['title']} is now available.")
            db.execute(
                "INSERT INTO audit_events(actor_id,action,target_type,target_id,created_at) VALUES(?,?,?,?,?)",
                (user["id"], "assignment_published", "assignment", assignment_id, now_ist()),
            )
            return jsonify({"status": "published"})

    @app.post("/api/assignments/<int:assignment_id>/submissions")
    @require_role("student")
    def submit_assignment(user, assignment_id):
        upload = request.files.get("file")
        if upload is None or not upload.filename:
            return api_error("Choose a file to submit.", 422)
        original_name = secure_filename(upload.filename)
        if not original_name or "." not in original_name:
            return api_error("The file name is invalid.", 415)
        extension = original_name.rsplit(".", 1)[1].lower()
        if extension not in ALLOWED_EXTENSIONS:
            return api_error("Allowed file types: PDF, DOCX, PPTX and ZIP.", 415)
        content = upload.stream.read(app.config["MAX_CONTENT_LENGTH"] + 1)
        if not content:
            return api_error("Empty files cannot be submitted.", 422)
        if len(content) > app.config["MAX_CONTENT_LENGTH"]:
            return api_error("Upload exceeds the configured 10 MB limit.", 413)
        if not valid_file_content(extension, content):
            return api_error("File content does not match the selected file type.", 415)
        with connect_db() as db:
            assignment = db.execute("SELECT * FROM assignments WHERE id=?", (assignment_id,)).fetchone()
            if not assignment or not student_can_see(db, user["id"], assignment_id):
                return api_error("Assignment not found.", 404)
            if assignment["status"] != "published":
                return api_error("This assignment is not accepting submissions.", 409)
            deadline = datetime.fromisoformat(assignment["due_at"])
            is_late = datetime.now(IST) > deadline
            policy = app.config["LATE_SUBMISSIONS"]
            if is_late and policy == "block":
                return api_error("The deadline has passed and late submissions are closed.", 409)
            previous = db.execute(
                "SELECT * FROM submissions WHERE assignment_id=? AND student_id=? ORDER BY version DESC LIMIT 1",
                (assignment_id, user["id"]),
            ).fetchone()
            if previous and not (assignment["allow_resubmissions"] and app.config["RESUBMISSIONS_ENABLED"]):
                return api_error("Resubmission is not enabled for this assignment.", 409)
            version = previous["version"] + 1 if previous else 1
            stored_name = f"{uuid.uuid4().hex}.{extension}"
            upload_path = Path(app.config["UPLOAD_FOLDER"]) / stored_name
            upload_path.write_bytes(content)
            try:
                cursor = db.execute(
                    """INSERT INTO submissions
                       (assignment_id,student_id,version,stored_name,original_name,mime_type,size,submitted_at,status)
                       VALUES(?,?,?,?,?,?,?,?,?)""",
                    (
                        assignment_id, user["id"], version, stored_name, original_name,
                        upload.mimetype or "application/octet-stream", len(content), now_ist(),
                        "late" if is_late else ("resubmitted" if version > 1 else "submitted"),
                    ),
                )
                submission_id = cursor.lastrowid
                db.execute(
                    "INSERT INTO audit_events(actor_id,action,target_type,target_id,created_at) VALUES(?,?,?,?,?)",
                    (user["id"], "submission_received", "submission", submission_id, now_ist()),
                )
            except Exception:
                upload_path.unlink(missing_ok=True)
                raise
            return jsonify(
                {"id": submission_id, "version": version, "submitted_at": now_ist(),
                 "status": "late" if is_late else ("resubmitted" if version > 1 else "submitted")}
            ), 201

    @app.get("/api/professor/assignments/<int:assignment_id>/submissions")
    @require_role("professor")
    def list_submissions(user, assignment_id):
        with connect_db() as db:
            if not professor_owns(db, user["id"], assignment_id):
                return api_error("Assignment not found.", 404)
            rows = db.execute(
                """SELECT s.id,s.student_id,s.version,s.original_name,s.size,s.submitted_at,s.status,
                          u.name AS student_name,u.usn,g.marks,g.feedback,g.published_at
                   FROM submissions s JOIN users u ON u.id=s.student_id
                   LEFT JOIN grades g ON g.submission_id=s.id
                   WHERE s.assignment_id=? AND s.version=(
                       SELECT MAX(s2.version) FROM submissions s2
                       WHERE s2.assignment_id=s.assignment_id AND s2.student_id=s.student_id)
                   ORDER BY s.submitted_at DESC""",
                (assignment_id,),
            ).fetchall()
            return jsonify({"submissions": [dict(row) for row in rows]})

    @app.get("/api/submissions/<int:submission_id>/download")
    @require_role("student", "professor", "admin")
    def download_submission(user, submission_id):
        with connect_db() as db:
            row = db.execute(
                """SELECT s.*,a.professor_id FROM submissions s JOIN assignments a ON a.id=s.assignment_id
                   WHERE s.id=?""",
                (submission_id,),
            ).fetchone()
            if not row:
                return api_error("Submission not found.", 404)
            authorized = (
                user["role"] == "admin"
                or (user["role"] == "professor" and row["professor_id"] == user["id"])
                or (user["role"] == "student" and row["student_id"] == user["id"])
            )
            if not authorized:
                return api_error("Submission not found.", 404)
            return send_from_directory(
                app.config["UPLOAD_FOLDER"], row["stored_name"],
                as_attachment=True, download_name=row["original_name"],
            )

    @app.post("/api/professor/submissions/<int:submission_id>/grade")
    @require_role("professor")
    def grade_submission(user, submission_id):
        data = request.get_json(silent=True) or {}
        try:
            marks = float(data.get("marks"))
        except (TypeError, ValueError):
            return api_error("Marks must be a valid number.", 422)
        if not (marks >= 0 and marks < float("inf")):
            return api_error("Marks must be a finite number at least zero.", 422)
        feedback = str(data.get("feedback", "")).strip()
        if len(feedback) > 5000:
            return api_error("Feedback must be 5000 characters or fewer.", 422)
        with connect_db() as db:
            row = db.execute(
                """SELECT s.id,a.id AS assignment_id,a.max_marks,a.professor_id
                   FROM submissions s JOIN assignments a ON a.id=s.assignment_id WHERE s.id=?""",
                (submission_id,),
            ).fetchone()
            if not row or row["professor_id"] != user["id"]:
                return api_error("Submission not found.", 404)
            if marks > row["max_marks"]:
                return api_error("Marks cannot exceed the assignment maximum.", 422)
            db.execute(
                """INSERT INTO grades(submission_id,marks,feedback,graded_by,graded_at)
                   VALUES(?,?,?,?,?) ON CONFLICT(submission_id) DO UPDATE SET
                   marks=excluded.marks,feedback=excluded.feedback,graded_by=excluded.graded_by,
                   graded_at=excluded.graded_at,published_at=NULL""",
                (submission_id, marks, feedback, user["id"], now_ist()),
            )
            db.execute(
                "INSERT INTO audit_events(actor_id,action,target_type,target_id,created_at) VALUES(?,?,?,?,?)",
                (user["id"], "submission_graded", "submission", submission_id, now_ist()),
            )
            return jsonify({"message": "Evaluation saved as a draft.", "published": False})

    @app.post("/api/professor/submissions/<int:submission_id>/publish-result")
    @require_role("professor")
    def publish_result(user, submission_id):
        with connect_db() as db:
            grade = db.execute(
                """SELECT g.id,s.assignment_id,a.professor_id FROM grades g
                   JOIN submissions s ON s.id=g.submission_id
                   JOIN assignments a ON a.id=s.assignment_id WHERE g.submission_id=?""",
                (submission_id,),
            ).fetchone()
            if not grade or grade["professor_id"] != user["id"]:
                return api_error("Evaluation not found.", 404)
            published_at = now_ist()
            db.execute("UPDATE grades SET published_at=? WHERE id=?", (published_at, grade["id"]))
            db.execute(
                "INSERT INTO notifications(user_id,title,message,created_at) SELECT student_id,'Result published','Your assignment result is ready to view.',? FROM submissions WHERE id=?",
                (published_at, submission_id),
            )
            db.execute(
                "INSERT INTO audit_events(actor_id,action,target_type,target_id,created_at) VALUES(?,?,?,?,?)",
                (user["id"], "result_published", "submission", submission_id, published_at),
            )
            return jsonify({"message": "Result published.", "published_at": published_at})

    @app.get("/api/notifications")
    @require_role("student", "professor", "admin")
    def notifications(user):
        with connect_db() as db:
            rows = db.execute(
                "SELECT id,title,message,created_at,is_read FROM notifications WHERE user_id=? ORDER BY created_at DESC LIMIT 50",
                (user["id"],),
            ).fetchall()
            return jsonify({"notifications": [dict(row) for row in rows]})

    @app.get("/api/admin/overview")
    @require_role("admin")
    def admin_overview(_user):
        with connect_db() as db:
            counts = {}
            for role in ("student", "professor", "admin"):
                counts[role + "s"] = db.execute(
                    "SELECT COUNT(*) FROM users WHERE role=? AND active=1", (role,)
                ).fetchone()[0]
            counts["subjects"] = db.execute("SELECT COUNT(DISTINCT subject) FROM user_subjects").fetchone()[0]
            counts["sections"] = db.execute(
                "SELECT COUNT(DISTINCT semester || '-' || section) FROM user_subjects"
            ).fetchone()[0]
            counts["assignments"] = db.execute("SELECT COUNT(*) FROM assignments").fetchone()[0]
            counts["submissions"] = db.execute("SELECT COUNT(*) FROM submissions").fetchone()[0]
            return jsonify({"counts": counts})

    @app.get("/api/admin/users")
    @require_role("admin")
    def admin_users(_user):
        with connect_db() as db:
            users = db.execute(
                "SELECT id,name,email,role,active,usn,semester,section FROM users ORDER BY role,name"
            ).fetchall()
            return jsonify({"users": [dict(user) for user in users]})

    @app.get("/api/admin/mappings")
    @require_role("admin")
    def admin_mappings(_user):
        with connect_db() as db:
            mappings = db.execute(
                """SELECT us.user_id,u.name,u.role,us.subject,us.semester,us.section
                   FROM user_subjects us JOIN users u ON u.id=us.user_id
                   ORDER BY us.semester,us.section,us.subject,u.name"""
            ).fetchall()
            return jsonify({"mappings": [dict(mapping) for mapping in mappings]})

    @app.post("/api/admin/mappings")
    @require_role("admin")
    def admin_add_mapping(_user):
        data = request.get_json(silent=True) or {}
        try:
            user_id = int(data.get("user_id"))
            semester = int(data.get("semester"))
        except (TypeError, ValueError):
            return api_error("Choose a valid user and semester.", 422)
        subject, section = str(data.get("subject", "")).strip(), str(data.get("section", "")).strip()
        if subject not in SUBJECTS or not 1 <= semester <= 8 or not section or len(section) > 10:
            return api_error("Choose a valid subject, semester and section.", 422)
        with connect_db() as db:
            target = db.execute("SELECT role FROM users WHERE id=? AND active=1", (user_id,)).fetchone()
            if not target or target["role"] == "admin":
                return api_error("Choose an active student or professor account.", 422)
            db.execute(
                "INSERT OR IGNORE INTO user_subjects(user_id,subject,semester,section) VALUES(?,?,?,?)",
                (user_id, subject, semester, section),
            )
        return jsonify({"message": "Subject and class mapping saved."}), 201

    @app.delete("/api/admin/mappings")
    @require_role("admin")
    def admin_remove_mapping(_user):
        data = request.get_json(silent=True) or {}
        try:
            user_id = int(data.get("user_id"))
            semester = int(data.get("semester"))
        except (TypeError, ValueError):
            return api_error("Choose a valid user and semester.", 422)
        subject, section = str(data.get("subject", "")).strip(), str(data.get("section", "")).strip()
        with connect_db() as db:
            cursor = db.execute(
                "DELETE FROM user_subjects WHERE user_id=? AND subject=? AND semester=? AND section=?",
                (user_id, subject, semester, section),
            )
            if not cursor.rowcount:
                return api_error("Subject mapping not found.", 404)
        return jsonify({"message": "Subject and class mapping removed."})

    @app.post("/api/admin/users")
    @require_role("admin")
    def admin_create_user(user):
        data = request.get_json(silent=True) or {}
        name, email = str(data.get("name", "")).strip(), str(data.get("email", "")).strip().lower()
        password, role = str(data.get("password", "")), str(data.get("role", ""))
        if not name or len(name) > 120 or "@" not in email or role not in ("student", "professor", "admin") or len(password) < 10:
            return api_error("Provide a name, valid email, role and password of at least 10 characters.", 422)
        try:
            with connect_db() as db:
                db.execute(
                    """INSERT INTO users(name,email,password_hash,role,usn,semester,section,created_at)
                       VALUES(?,?,?,?,?,?,?,?)""",
                    (name, email, generate_password_hash(password), role,
                     data.get("usn") or None, data.get("semester") or None,
                     data.get("section") or None, now_ist()),
                )
        except sqlite3.IntegrityError:
            return api_error("An account with that email already exists.", 409)
        return jsonify({"message": "Account created."}), 201

    @app.patch("/api/admin/users/<int:user_id>/status")
    @require_role("admin")
    def admin_update_user(user, user_id):
        data = request.get_json(silent=True) or {}
        if not isinstance(data.get("active"), bool):
            return api_error("Active must be true or false.", 422)
        if user_id == user["id"] and not data["active"]:
            return api_error("You cannot deactivate your own account.", 409)
        with connect_db() as db:
            cursor = db.execute("UPDATE users SET active=? WHERE id=?", (int(data["active"]), user_id))
            if not cursor.rowcount:
                return api_error("User not found.", 404)
        return jsonify({"message": "Account status updated."})

    return app


def parse_deadline(value):
    parsed = datetime.fromisoformat(str(value))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=IST)
    return parsed.astimezone(IST)


def valid_file_content(extension, content):
    if extension == "pdf":
        return content.startswith(b"%PDF-")
    if extension in {"docx", "pptx"}:
        if not content.startswith(b"PK"):
            return False
        try:
            with zipfile.ZipFile(BytesIO(content)) as archive:
                required = "word/document.xml" if extension == "docx" else "ppt/presentation.xml"
                return required in archive.namelist()
        except zipfile.BadZipFile:
            return False
    return content.startswith(b"PK")


app = create_app()


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")
