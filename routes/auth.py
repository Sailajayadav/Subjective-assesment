from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app
from werkzeug.security import generate_password_hash, check_password_hash
import models

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

@auth_bp.route("/signup", methods=["GET","POST"])
def signup():
    if request.method == "POST":
        name = request.form["name"].strip()
        email = request.form["email"].strip().lower()
        password = request.form["password"]
        if models.find_user_by_email(email):
            flash("Email already registered. Please login.", "warning")
            return redirect(url_for("auth.login"))
        hashed = generate_password_hash(password)
        models.create_user(name, email, hashed)
        flash("Signup successful. Please login.", "success")
        return redirect(url_for("auth.login"))
    return render_template("signup.html")

@auth_bp.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]
        user = models.find_user_by_email(email)
        if not user or not check_password_hash(user["password"], password):
            flash("Invalid credentials", "danger")
            return redirect(url_for("auth.login"))
        
        # Set session
        session["user"] = {"name": user["name"], "email": user["email"]}
        
        # Redirect to the first available test
        first_test = list(models.tests_col().find({}, {"id": 1}, limit=1))
        if first_test:
            test_id = first_test[0]["id"]
            return redirect(url_for("test.start", test_id=test_id))
        else:
            flash("No tests available", "warning")
            return redirect(url_for("home"))

    return render_template("login.html")


@auth_bp.route("/logout")
def logout():
    session.pop("user", None)
    flash("Logged out", "info")
    return redirect(url_for("home"))
