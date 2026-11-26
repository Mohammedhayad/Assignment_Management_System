import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from app import create_app


class AssignmentPortalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.app = create_app(
            {
                "TESTING": True,
                "SECRET_KEY": "test-secret",
                "DATABASE": str(root / "test.sqlite3"),
                "UPLOAD_FOLDER": str(root / "uploads"),
                "MAX_CONTENT_LENGTH": 1024 * 1024,
            }
        )
        self.client = self.app.test_client()

    def tearDown(self):
        self.temp.cleanup()

    def login(self, email, password):
        response = self.client.post(
            "/api/auth/login",
            json={"email": email, "password": password},
        )
        self.assertEqual(response.status_code, 200)
        self.csrf = response.json["csrf_token"]

    def post_json(self, url, payload):
        return self.client.post(
            url,
            data=json.dumps(payload),
            content_type="application/json",
            headers={"X-CSRF-Token": self.csrf},
        )

    def test_student_cannot_access_professor_resources_and_only_sees_mapped_work(self):
        self.login("student@bmsit.edu", "Student123!")
        response = self.client.get("/api/student/assignments")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json["assignments"]), 1)
        self.assertEqual(self.client.get("/api/professor/assignments").status_code, 403)
        self.assertEqual(self.client.get("/api/assignments/999").status_code, 404)

    def test_professor_creates_and_publishes_draft_for_authorized_class(self):
        self.login("professor@bmsit.edu", "Professor123!")
        payload = {
            "subject": "Data Structures",
            "semester": 3,
            "section": "A",
            "title": "Trees",
            "description": "Implement a binary search tree.",
            "due_at": "2030-12-01T23:59",
            "max_marks": 20,
        }
        created = self.post_json("/api/professor/assignments", payload)
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.json["status"], "draft")
        published = self.post_json(f"/api/assignments/{created.json['id']}/publish", {})
        self.assertEqual(published.status_code, 200)
        forbidden = dict(payload, section="B")
        self.assertEqual(self.post_json("/api/professor/assignments", forbidden).status_code, 403)

    def test_submission_is_private_and_result_is_hidden_until_published(self):
        self.login("student@bmsit.edu", "Student123!")
        pdf = b"%PDF-1.4\nsample document"
        submitted = self.client.post(
            "/api/assignments/1/submissions",
            data={"file": (io.BytesIO(pdf), "work.pdf")},
            headers={"X-CSRF-Token": self.csrf},
        )
        self.assertEqual(submitted.status_code, 201)
        submission_id = submitted.json["id"]

        self.client.post("/api/auth/logout", headers={"X-CSRF-Token": self.csrf})
        self.login("professor@bmsit.edu", "Professor123!")
        self.assertEqual(self.post_json(f"/api/professor/submissions/{submission_id}/grade", {"marks": 21}).status_code, 422)
        self.assertEqual(self.post_json(f"/api/professor/submissions/{submission_id}/grade", {"marks": 18, "feedback": "Good work."}).status_code, 200)

        self.client.post("/api/auth/logout", headers={"X-CSRF-Token": self.csrf})
        self.login("student@bmsit.edu", "Student123!")
        assignment = self.client.get("/api/student/assignments").json["assignments"][0]
        self.assertIsNone(assignment["marks"])

        self.client.post("/api/auth/logout", headers={"X-CSRF-Token": self.csrf})
        self.login("professor@bmsit.edu", "Professor123!")
        self.assertEqual(self.post_json(f"/api/professor/submissions/{submission_id}/publish-result", {}).status_code, 200)
        self.client.post("/api/auth/logout", headers={"X-CSRF-Token": self.csrf})
        self.login("student@bmsit.edu", "Student123!")
        assignment = self.client.get("/api/student/assignments").json["assignments"][0]
        self.assertEqual(assignment["marks"], 18)
        self.client.post("/api/auth/logout", headers={"X-CSRF-Token": self.csrf})
        self.login("student2@bmsit.edu", "Student123!")
        self.assertEqual(self.client.get(f"/api/submissions/{submission_id}/download").status_code, 404)

    def test_file_type_validation_rejects_mismatched_or_unsupported_content(self):
        self.login("student@bmsit.edu", "Student123!")
        bad_pdf = self.client.post(
            "/api/assignments/1/submissions",
            data={"file": (io.BytesIO(b"not a pdf"), "work.pdf")},
            headers={"X-CSRF-Token": self.csrf},
        )
        self.assertEqual(bad_pdf.status_code, 415)
        unsupported = self.client.post(
            "/api/assignments/1/submissions",
            data={"file": (io.BytesIO(b"binary"), "program.exe")},
            headers={"X-CSRF-Token": self.csrf},
        )
        self.assertEqual(unsupported.status_code, 415)

    def test_docx_package_signature_is_checked(self):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("word/document.xml", "<document/>")
        self.login("student@bmsit.edu", "Student123!")
        response = self.client.post(
            "/api/assignments/1/submissions",
            data={"file": (io.BytesIO(buffer.getvalue()), "assignment.docx")},
            headers={"X-CSRF-Token": self.csrf},
        )
        self.assertEqual(response.status_code, 201)

    def test_admin_can_map_new_professor_to_class_and_subject(self):
        self.login("admin@bmsit.edu", "Admin123!")
        created = self.post_json(
            "/api/admin/users",
            {
                "name": "New Professor",
                "email": "new.professor@bmsit.edu",
                "password": "Temporary123!",
                "role": "professor",
            },
        )
        self.assertEqual(created.status_code, 201)
        users = self.client.get("/api/admin/users").json["users"]
        professor_id = next(user["id"] for user in users if user["email"] == "new.professor@bmsit.edu")
        mapped = self.post_json(
            "/api/admin/mappings",
            {
                "user_id": professor_id,
                "subject": "Data Structures",
                "semester": 3,
                "section": "A",
            },
        )
        self.assertEqual(mapped.status_code, 201)
        self.client.post("/api/auth/logout", headers={"X-CSRF-Token": self.csrf})
        self.login("new.professor@bmsit.edu", "Temporary123!")
        assignment = self.post_json(
            "/api/professor/assignments",
            {
                "subject": "Data Structures",
                "semester": 3,
                "section": "A",
                "title": "New class assignment",
                "description": "Complete the assigned exercise.",
                "due_at": "2030-12-01T23:59",
                "max_marks": 20,
            },
        )
        self.assertEqual(assignment.status_code, 201)


if __name__ == "__main__":
    unittest.main()
