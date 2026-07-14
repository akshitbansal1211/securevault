from flask import Flask

app = Flask(__name__)


@app.route("/")
def home():
    return "Hello, SecureVault!"


@app.route("/about")
def about():
    return "SecureVault — built by Akshit, a document management system."


if __name__ == "__main__":
    app.run(debug=True)