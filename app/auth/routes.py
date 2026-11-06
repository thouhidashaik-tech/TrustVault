from flask import (
    Blueprint, render_template, request,
    redirect, url_for, flash
)
from flask_login import login_user, logout_user, login_required
from sqlalchemy import select
from app.extensions import db
from app.models import User

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not full_name or not email or not password:
            flash("Please fill in all fields.", "error")
            return redirect(url_for("auth.register"))

        if len(password) < 12:
            flash("Password must contain at least 12 characters.", "error")
            return redirect(url_for("auth.register"))

        existing_user = db.session.execute(
            select(User).where(User.email == email)
        ).scalar_one_or_none()

        if existing_user:
            flash("An account with this email already exists.", "error")
            return redirect(url_for("auth.register"))

        user = User(
            full_name=full_name,
            email=email,
            role="viewer"
        )
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        flash("Registration successful. Please log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register.html")



@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = db.session.execute(
            select(User).where(User.email == email)
        ).scalar_one_or_none()

        if user and user.is_active and user.check_password(password):
            login_user(user)
            flash("Welcome to TrustVault!", "success")

            if user.role == "admin":
                return redirect(url_for("admin.dashboard"))

            elif user.role == "owner":
                return redirect(url_for("documents.dashboard"))

            else:
                return redirect(url_for("documents.shared_documents"))

        flash("Invalid email or password.", "error")

    return render_template("auth/login.html")

@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "success")
    return redirect(url_for("auth.login"))