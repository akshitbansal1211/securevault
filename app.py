from flask import Flask, render_template, request, redirect, url_for
from werkzeug.security import generate_password_hash
from database import get_connection, init_db

app = Flask(__name__)
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
        conn.execute(
            "INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
            (username, email, hashed_password)
        )
        conn.commit()
        conn.close()

        return redirect(url_for("home"))

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    return render_template("login.html")


if __name__ == "__main__":
    app.run(debug=True)