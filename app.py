import os
import uuid
from werkzeug.utils import secure_filename
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_connection, init_db
from auth import login_required
app = Flask(__name__)
app.secret_key = "dev-secret-key-change-this-later"
UPLOAD_FOLDER = "static/uploads"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "pdf"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

init_db()  # creates the table if it doesn't exist yet, runs once at startup


@app.route("/")
def home():
    return "Hello, SecureVault!"


@app.route("/about")
def about():
    return "SecureVault — built by Akshit, a document management system."


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]

        hashed_password = generate_password_hash(password)

        conn = get_connection()
        try:
            conn.execute(
                "INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
                (username, email, hashed_password)
            )
            conn.commit()
        except sqlite3.IntegrityError:
            flash("Username or email already exists. Please choose another.", "error")
            return redirect(url_for("register"))
        finally:
            conn.close()

        flash("Registration successful! Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_connection()
        user = conn.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()
        conn.close()

        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            return redirect(url_for("dashboard"))
        else:

            flash("Invalid username or password.", "error")
            return redirect(url_for("login"))

    return render_template("login.html")

@app.route("/dashboard")
@login_required
def dashboard():
    files = []  # placeholder — real file list comes Day 13-14
    return render_template("dashboard.html", username=session["username"], files=files)

@app.route("/profile")
@login_required
def profile():
    return f"This is {session['username']}'s profile page."


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))

@app.route("/upload", methods=["GET", "POST"])
@login_required
def upload():
    if request.method == "POST":
        file = request.files.get("file")

        if not file or file.filename == "":
            flash("No file selected.", "error")
            return redirect(url_for("upload"))

        if not allowed_file(file.filename):
            flash("Invalid file type. Only PNG, JPG, and PDF are allowed.", "error")
            return redirect(url_for("upload"))

        original_name = secure_filename(file.filename)
        unique_name = f"{uuid.uuid4().hex}_{original_name}"
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], unique_name)
        file.save(filepath)

        flash(f"'{original_name}' uploaded successfully!", "success")
        return redirect(url_for("dashboard"))

    return render_template("upload.html", username=session["username"])

if __name__ == "__main__":
    app.run(debug=True)
    