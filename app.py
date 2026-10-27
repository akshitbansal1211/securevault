import os
import uuid
from io import BytesIO
from datetime import timezone, timedelta

import psycopg
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file, abort
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from supabase import create_client
from database import get_connection, init_db
from auth import login_required

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-change-this-later")

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "pdf"}
BUCKET_NAME = "securevault-files"
LEGACY_UPLOAD_FOLDER = os.path.join("static", "uploads")


def supabase_client():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise RuntimeError("Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in Render.")
    return create_client(url, key)


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def object_path(owner_id, stored_name):
    return f"{owner_id}/{stored_name}"


def get_owned_file(file_id):
    conn = get_connection()
    try:
        return conn.execute(
            "SELECT * FROM files WHERE id = %s AND owner_id = %s",
            (file_id, session["user_id"])
        ).fetchone()
    finally:
        conn.close()


def read_file(file_record):
    path = object_path(file_record["owner_id"], file_record["stored_name"])
    try:
        result = supabase_client().storage.from_(BUCKET_NAME).download(path)
        return result if isinstance(result, bytes) else bytes(result)
    except Exception:
        # Compatibility for old uploads still present on this Render instance.
        old_path = os.path.join(LEGACY_UPLOAD_FOLDER, file_record["stored_name"])
        if os.path.isfile(old_path):
            with open(old_path, "rb") as f:
                return f.read()
        abort(404)


init_db()


@app.route("/")
def home():
    return redirect(url_for("dashboard" if "user_id" in session else "login"))


@app.route("/about")
def about():
    return "SecureVault — built by Akshit, a document management system."


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"].strip()
        email = request.form["email"].strip()
        password = request.form["password"]
        conn = get_connection()
        try:
            conn.execute(
                "INSERT INTO users (username, email, password) VALUES (%s, %s, %s)",
                (username, email, generate_password_hash(password))
            )
            conn.commit()
        except psycopg.errors.UniqueViolation:
            conn.rollback()
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
        username = request.form["username"].strip()
        password = request.form["password"]
        conn = get_connection()
        try:
            user = conn.execute(
                "SELECT * FROM users WHERE username = %s", (username,)
            ).fetchone()
        finally:
            conn.close()
        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            return redirect(url_for("dashboard"))
        flash("Invalid username or password.", "error")
        return redirect(url_for("login"))
    return render_template("login.html")


@app.route("/dashboard")
@login_required
def dashboard():
    term = request.args.get("search", "").strip()
    conn = get_connection()
    try:
        if term:
            files = conn.execute(
                """SELECT * FROM files WHERE owner_id = %s
                   AND original_name ILIKE %s ORDER BY uploaded_at DESC""",
                (session["user_id"], f"%{term}%")
            ).fetchall()
        else:
            files = conn.execute(
                "SELECT * FROM files WHERE owner_id = %s ORDER BY uploaded_at DESC",
                (session["user_id"],)
            ).fetchall()
    finally:
        conn.close()

    ist = timezone(timedelta(hours=5, minutes=30))
    files_local = []
    for item in files:
        d = dict(item)
        uploaded_at = d["uploaded_at"]
        if uploaded_at.tzinfo is None:
            uploaded_at = uploaded_at.replace(tzinfo=timezone.utc)
        d["uploaded_at"] = uploaded_at.astimezone(ist).strftime("%Y-%m-%d %I:%M %p")
        files_local.append(d)
    return render_template(
        "dashboard.html", username=session["username"],
        files=files_local, search_term=term
    )


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
    if request.method != "POST":
        return render_template("upload.html", username=session["username"])

    uploaded = request.files.get("file")
    if not uploaded or not uploaded.filename:
        flash("No file selected.", "error")
        return redirect(url_for("upload"))
    if not allowed_file(uploaded.filename):
        flash("Invalid file type. Only PNG, JPG, JPEG, and PDF are allowed.", "error")
        return redirect(url_for("upload"))

    original_name = secure_filename(uploaded.filename)
    if not original_name:
        flash("Invalid filename.", "error")
        return redirect(url_for("upload"))

    owner_id = session["user_id"]
    stored_name = f"{uuid.uuid4().hex}_{original_name}"
    path = object_path(owner_id, stored_name)
    data = uploaded.read()
    content_type = uploaded.mimetype or "application/octet-stream"

    try:
        supabase_client().storage.from_(BUCKET_NAME).upload(
            path, data,
            file_options={"content-type": content_type, "upsert": "false"}
        )
    except Exception:
        app.logger.exception("Supabase Storage upload failed")
        flash("Upload failed. Please try again.", "error")
        return redirect(url_for("upload"))

    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO files (owner_id, original_name, stored_name) VALUES (%s, %s, %s)",
            (owner_id, original_name, stored_name)
        )
        conn.commit()
    except Exception:
        conn.rollback()
        try:
            supabase_client().storage.from_(BUCKET_NAME).remove([path])
        except Exception:
            app.logger.exception("Cleanup of uploaded object failed")
        app.logger.exception("File metadata insert failed")
        flash("The file could not be saved to your account.", "error")
        return redirect(url_for("upload"))
    finally:
        conn.close()

    flash(f"'{original_name}' uploaded successfully!", "success")
    return redirect(url_for("dashboard"))


@app.route("/download/<int:file_id>")
@login_required
def download(file_id):
    record = get_owned_file(file_id)
    if record is None:
        abort(404)
    data = read_file(record)
    return send_file(
        BytesIO(data), as_attachment=True,
        download_name=record["original_name"],
        mimetype="application/octet-stream"
    )


@app.route("/preview/<int:file_id>")
@login_required
def preview(file_id):
    record = get_owned_file(file_id)
    if record is None:
        abort(404)
    data = read_file(record)
    ext = record["original_name"].rsplit(".", 1)[-1].lower()
    mime = "application/pdf" if ext == "pdf" else (
        "image/jpeg" if ext in {"jpg", "jpeg"} else "image/png"
    )
    response = send_file(
        BytesIO(data), mimetype=mime, as_attachment=False,
        download_name=record["original_name"]
    )
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Cache-Control"] = "private, no-store"
    return response


@app.route("/delete/<int:file_id>", methods=["POST"])
@login_required
def delete(file_id):
    record = get_owned_file(file_id)
    if record is None:
        abort(404)

    path = object_path(record["owner_id"], record["stored_name"])
    legacy_path = os.path.join(LEGACY_UPLOAD_FOLDER, record["stored_name"])
    try:
        supabase_client().storage.from_(BUCKET_NAME).remove([path])
    except Exception:
        # Old local-only uploads may not exist in Supabase Storage.
        if not os.path.isfile(legacy_path):
            app.logger.exception("Supabase Storage delete failed")
            flash("Could not delete the stored file. Please try again.", "error")
            return redirect(url_for("dashboard"))

    conn = get_connection()
    try:
        conn.execute(
            "DELETE FROM files WHERE id = %s AND owner_id = %s",
            (record["id"], session["user_id"])
        )
        conn.commit()
    except Exception:
        conn.rollback()
        app.logger.exception("Database delete failed")
        flash("Storage deletion occurred, but the database record could not be deleted.", "error")
        return redirect(url_for("dashboard"))
    finally:
        conn.close()

    if os.path.isfile(legacy_path):
        try:
            os.remove(legacy_path)
        except OSError:
            app.logger.exception("Could not remove legacy local file")
    flash(f"'{record['original_name']}' deleted successfully.", "success")
    return redirect(url_for("dashboard"))


@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404


@app.errorhandler(500)
def server_error(e):
    return render_template("500.html"), 500


if __name__ == "__main__":
    app.run(debug=True)
