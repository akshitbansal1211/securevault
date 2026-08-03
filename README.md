# 🔐 SecureVault

**SecureVault** is an enterprise-style document management system built with Flask and SQLite — featuring secure user authentication, file upload/download, in-browser image and PDF preview, and search. Built from scratch as a hands-on learning project, with a deliberate focus on understanding *why* each piece works, not just making it work.

## Features

- **User authentication** — registration and login with hashed passwords (Werkzeug/scrypt), session-based auth, and route protection via a custom decorator
- **File management** — upload, download, and per-user file listing backed by a relational SQLite schema
- **In-browser preview** — images and PDFs render directly in a modal, no download required
- **Search** — filter your files by name using SQL `LIKE` pattern matching
- **Responsive design** — fully usable on mobile and tablet screens, not just desktop
- **Flash messaging** — clear success/error feedback across registration, login, upload, and logout
- **Custom error pages** — branded 404/500 pages instead of raw Flask defaults

## Security

This project was built with real security practices in mind, not just "does it work":

- Passwords hashed with scrypt (via Werkzeug), never stored in plain text
- All SQL queries parameterized — no string-concatenated queries, protecting against SQL injection
- Session cookies signed via a secret key, `HttpOnly` flag enabled
- Uploaded filenames sanitized (`secure_filename`) and given collision-proof unique names (UUID-based) to prevent path traversal and overwrite attacks
- File uploads validated against an extension allow-list
- Every file-access route (`download`, `preview`) enforces ownership checks (`WHERE id = ? AND owner_id = ?`) to prevent IDOR (Insecure Direct Object Reference) — verified through manual cross-account testing during development

## Tech Stack

- **Backend:** Python, Flask
- **Database:** SQLite
- **Frontend:** HTML5, CSS3 (hand-written, no frameworks), vanilla JavaScript (preview modal)
- **Auth:** Flask sessions, Werkzeug password hashing

## Project Structure

securevault/
├── app.py                 # Main Flask application and routes
├── database.py             # Database connection and schema setup
├── auth.py                 # login_required decorator
├── requirements.txt
├── static/
│   ├── style.css
│   └── uploads/
│       └── .gitkeep         # Keeps the folder tracked; actual uploads are gitignored
├── templates/
│   ├── register.html
│   ├── login.html
│   ├── dashboard.html
│   ├── upload.html
│   ├── 404.html
│   └── 500.html
└── README.md

## Setup & Installation

```bash
# Clone the repository
git clone https://github.com/akshitbansal1211/securevault.git
cd securevault

# Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Run the app
python app.py
```
Then visit `http://127.0.0.1:5000` in your browser.

## Screenshots

*(Coming soon)*

## Future Work (v1.1+)

- **Multi-tenancy** — isolated private workspaces so multiple organizations can use SecureVault independently, without seeing each other's users or files
- File versioning / edit history
- Admin dashboard with user management
- Two-factor authentication
- Cloud storage (S3) instead of local disk

## About

Built by [Akshit Bansal](https://github.com/akshitbansal1211) as a self-directed full-stack learning project — covering HTML/CSS fundamentals, Flask, relational database design, authentication, session management, and real web security practices from first principles.