import os
import subprocess
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.utils import secure_filename
from serpapi import GoogleSearch
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

UPLOAD_FOLDER = "uploads"
app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["SECRET_KEY"] = "my-secret-key"  
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:////tmp/test.db"
db = SQLAlchemy(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        if User.query.filter_by(username=username).first():
            flash("Username already exists")
            return redirect(url_for("register"))
        user = User(username=username, password_hash=generate_password_hash(password))
        db.session.add(user)
        db.session.commit()
        return redirect(url_for("login"))
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user = User.query.filter_by(username=username).first()
        if user is None or not check_password_hash(user.password_hash, password):
            flash("Please check your login details and try again.")
            return redirect(url_for("login"))
        session["username"] = username
        return redirect(url_for("profile"))
    return render_template("login.html")


@app.route("/profile")
def profile():
    if "username" not in session:
        return redirect(url_for("login"))
    return render_template("profile.html", username=session["username"])


@app.route("/logout")
def logout():
    session.pop("username", None)
    return redirect(url_for("index"))


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/index")
def index():
    return render_template("index.html")


def upload_image(image_path):
    """
    Uploads an image to an image hosting service using the command-line utility "images-upload-cli".

    Parameters:
    image_path (str): The path of the image file to upload.

    Returns:
    str: The URL of the uploaded image, or None if an error occurred.
    """
    try:
        result = subprocess.run(
            ["images-upload-cli", "-h", "imgur", image_path],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            image_url = result.stdout.strip()
            print(f"Image uploaded successfully: {image_url}")
            return image_url
        else:
            print(f"Error uploading image: {result.stderr.strip()}")
            return None
    except Exception as e:
        print(f"Error uploading image: {str(e)}")
        return None


@app.route("/search", methods=["POST"])
def upload_file():
    if "username" not in session:
        return redirect(url_for("login"))
    query = request.form.get("query", "")
    if "file" not in request.files:
        flash("No file part in the request")
        return redirect(request.url)
    file = request.files["file"]
    if file.filename == "":
        flash("No file selected for uploading")
        return redirect(request.url)
    if file:
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(file_path)
        image_url = upload_image(file_path)
        if image_url is not None:
            params = {
                "q": query + "Shopping, India",  # use the custom query here
                "engine": "google_lens",
                "url": image_url,
                "api_key": "060be4888eac5deea181e65fc0781dfca34e3431b4fc5ce9aa059f929cf9c22c",
            }

            search = GoogleSearch(params)
            results = search.get_dict()
            visual_matches = results["visual_matches"]

            without_price = [
                result
                for result in visual_matches
                if "price" not in result or "value" not in result["price"]
            ]
            with_price = [
                result
                for result in visual_matches
                if "price" in result and "value" in result["price"]
            ]

            for result in with_price:
                result["price"]["extracted_value"] = float(
                    result["price"]["extracted_value"]
                )

            with_price = sorted(with_price, key=lambda k: k["price"]["extracted_value"])
            visual_matches = without_price + with_price[:20]
            return render_template("results.html", results=visual_matches)
        else:
            return "Error uploading image"
    return redirect(request.url)


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)

