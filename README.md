# BMSIT CSE – Assignment Management System

A web-based Assignment Management System developed for the **Computer Science and Engineering Department of BMS Institute of Technology and Management (BMSIT)**.

The application aims to simplify the process of assignment creation, distribution, submission, evaluation, and result tracking through a centralized platform for students and professors.

---

## 📌 Project Overview

The Assignment Management System provides a common platform where professors can create and publish assignments for their respective classes, while students can view assignment details, upload completed work, and track their submission status.

The system also supports evaluation, marks, feedback, and result publication.

The application follows a **client-server architecture** in which the frontend communicates with the Flask backend through REST APIs.

## 🎯 Objectives

- Centralize assignment creation and submission.
- Reduce manual paperwork and communication gaps.
- Enable professors to manage and evaluate assignments.
- Allow students to track assignment deadlines and submission status.
- Provide secure, role-based access to academic information.
- Maintain assignment and submission history.

## ✨ Key Features

### 👨‍🎓 Student Module
- Secure student login.
- Personalized student dashboard.
- View assignments based on semester, section, and subject.
- View assignment instructions and deadlines.
- Download professor-provided attachments.
- Upload completed assignments.
- Track submission status and timestamps.
- Resubmit assignments when permitted.
- View marks and feedback after result publication.
- Receive in-app notifications.

### 👨‍🏫 Professor Module
- Secure professor login.
- Professor dashboard.
- Create and manage assignments.
- Save assignments as drafts or publish them.
- Select subject, semester, section, and deadline.
- Attach reference materials to assignments.
- View student submissions.
- Download submitted files.
- Evaluate assignments and enter marks.
- Provide feedback to students.
- Publish results.

### 🛡️ Administrator Module
- Manage student and professor accounts.
- Manage subjects, semesters, and sections.
- Configure professor-subject mappings.
- View system-level reports.
- Manage system configurations.

*Note: Administrator functionality is subject to the final approved project scope.*

## 🛠️ Technology Stack

| Component | Technology |
|---|---|
| Frontend | HTML5, CSS3, JavaScript |
| Frontend-Backend Communication | AJAX / Fetch API |
| Backend | Python |
| Backend Framework | Flask |
| Database | SQLite |
| API Architecture | REST API |
| Version Control | Git and GitHub |

## 🏗️ System Architecture

The application follows a three-layer architecture:

1. **Presentation Layer:** HTML, CSS, and JavaScript provide the user interface.
2. **Application Layer:** Flask handles REST API requests, authentication, validation, and business logic.
3. **Data Layer:** SQLite stores user details, assignments, submissions, marks, and other application records.

```text
          STUDENT / PROFESSOR / ADMIN
                       |
                       v
              FRONTEND INTERFACE
             HTML | CSS | JavaScript
                       |
                       v
                AJAX / FETCH API
                       |
                       v
                FLASK BACKEND
                 REST APIs
                       |
             +---------+---------+
             |                   |
             v                   v
       SQLITE DATABASE       FILE STORAGE
       User Records          Assignment Files
       Assignments           Submitted Files
       Submissions
       Marks & Feedback
```

## 📂 Project Structure

The proposed project structure is:

```text
BMSIT-Assignment-Management/
│
├── app/
│   ├── __init__.py
│   ├── models/
│   ├── routes/
│   │   ├── auth.py
│   │   ├── student.py
│   │   ├── professor.py
│   │   └── admin.py
│   │
│   ├── services/
│   ├── utils/
│   ├── templates/
│   └── static/
│       ├── css/
│       ├── js/
│       └── images/
│
├── uploads/
├── tests/
├── config.py
├── run.py
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

*The structure may evolve during development.*

## ⚙️ Installation and Setup

Follow these steps to run the project locally.

### 1. Clone the Repository

```bash
git clone <YOUR_REPOSITORY_URL>
```

### 2. Navigate to the Project Directory

```bash
cd BMSIT-Assignment-Management
```

### 3. Create a Virtual Environment

```bash
python -m venv venv
```

Activate it:

**Windows:**
```bash
venv\Scripts\activate
```

**Linux / macOS:**
```bash
source venv/bin/activate
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. Configure Environment Variables

Create a `.env` file based on `.env.example` and configure the required application settings.

Never commit passwords, secret keys, or other sensitive configuration values to GitHub.

### 6. Run the Application

```bash
python run.py
```

Open the application in your browser at:

```text
http://127.0.0.1:5000/
```

*Setup commands may need adjustment according to the final implementation.*

## 🔗 REST API Overview

The frontend communicates with the backend through REST API endpoints.

| HTTP Method | Endpoint | Description |
|---|---|---|
| POST | `/api/auth/login` | User login |
| POST | `/api/auth/logout` | User logout |
| GET | `/api/me` | Get logged-in user details |
| GET | `/api/student/assignments` | View student assignments |
| GET | `/api/assignments/{id}` | View assignment details |
| POST | `/api/professor/assignments` | Create assignment |
| PUT | `/api/professor/assignments/{id}` | Update assignment |
| POST | `/api/assignments/{id}/publish` | Publish assignment |
| POST | `/api/assignments/{id}/submissions` | Upload submission |
| GET | `/api/professor/assignments/{id}/submissions` | View submissions |
| GET | `/api/submissions/{id}/download` | Download submission |
| POST | `/api/professor/submissions/{id}/grade` | Evaluate submission |
| POST | `/api/professor/submissions/{id}/publish-result` | Publish result |
| GET | `/api/notifications` | View notifications |

*These endpoints represent the proposed API design. Actual availability depends on implementation.*

## 🧪 Testing

Testing is an important part of this project to ensure reliability, security, and correct functionality.

The testing process covers:

- Unit Testing
- API Testing
- Integration Testing
- Functional Testing
- Database Testing
- Security Testing
- Performance Testing
- Responsive UI Testing
- Regression Testing
- User Acceptance Testing (UAT)

### Important Test Scenarios

- Verify valid and invalid login attempts.
- Verify role-based access restrictions.
- Verify assignment creation and publication.
- Verify assignment visibility for the correct class.
- Verify valid and invalid file uploads.
- Verify late submission and resubmission policies.
- Verify marks and feedback validation.
- Verify that results remain hidden until publication.
- Verify that users cannot access unauthorized submissions.
- Verify application behavior on different screen sizes.

A detailed Software Test Plan (STP) is maintained as a separate project document.

## 🔐 Security Considerations

- Passwords must be stored using secure password hashing.
- Protected APIs must enforce authentication and authorization.
- Students must not access other students' submissions.
- Professors must only manage assignments within their authorized scope.
- File uploads must be validated on the server.
- Uploaded files must use generated server-side filenames.
- Sensitive files must be served through authorized download endpoints.
- Database queries must use parameterized statements.
- Secrets and credentials must not be committed to the repository.

## 🚀 Future Enhancements

- Email notifications.
- Plagiarism detection integration.
- Advanced assignment analytics.
- Bulk assignment and submission management.
- Export reports in PDF and Excel formats.
- Support for additional departments.
- Migration from SQLite to PostgreSQL for larger deployments.

## 👥 Project Team

**Department:** Computer Science and Engineering  
**Institution:** BMS Institute of Technology and Management (BMSIT)

Developed collaboratively by the project team.

| Name | Role | GitHub Profile |
|---|---|---|
| Team Member 1 | Developer | [GitHub](https://github.com/) |
| Team Member 2 | Developer | [GitHub](https://github.com/) |
| Team Member 3 | Developer | [GitHub](https://github.com/) |

*Replace the sample entries with actual team member details.*

## 📌 Project Status

**Status:** Under Development

The project is being developed incrementally, beginning with authentication, role-based dashboards, assignment creation, submission management, and evaluation.

## 📄 Documentation

Project documentation includes:

- Software Requirements Specification (SRS)
- System Architecture Design
- Database Design
- REST API Design
- Software Test Plan (STP)
- Test Case Documentation

## 🤝 Contributions

Contributions from team members are welcome.

1. Create a new branch for your feature or bug fix.
2. Make the required changes.
3. Test your changes before committing.
4. Push your branch to GitHub.
5. Create a Pull Request for review.

## 📜 License

This project is developed for academic purposes at BMS Institute of Technology and Management.

A formal open-source license can be added if the project is intended for public reuse.

---

**BMSIT CSE – Assignment Management System**  
*Simplifying Assignment Management Through Technology.*
