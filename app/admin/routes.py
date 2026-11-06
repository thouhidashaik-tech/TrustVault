
from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    abort,
    current_app,
)
from flask_login import current_user
from sqlalchemy.exc import IntegrityError
import re

from app.extensions import db
from app.models import User, Document, AuditEvent, DocumentPermission
from app.permissions import roles_required
from app.audit import add_audit_event
from datetime import datetime


admin_bp = Blueprint(
    "admin",
    __name__,
    url_prefix="/admin"
)


@admin_bp.route("/dashboard")
@roles_required("admin")
def dashboard():

    users = User.query.order_by(
        User.created_at.desc()
    ).all()

    document_count = Document.query.count()
    audit_count = AuditEvent.query.count()

    return render_template(
        "admin/dashboard.html",
        users=users,
        user_count=len(users),
        document_count=document_count,
        audit_count=audit_count
    )


@admin_bp.route("/activity")
@roles_required("admin")
def activity():

    activities = (
        db.session.query(
            AuditEvent,
            User.full_name,
            Document.title
        )
        .outerjoin(
            User,
            AuditEvent.actor_user_id == User.id
        )
        .outerjoin(
            Document,
            AuditEvent.document_id == Document.id
        )
        .order_by(AuditEvent.timestamp.desc())
        .limit(200)
        .all()
    )

    return render_template(
        "admin/activity.html",
        activities=activities
    )


@admin_bp.route("/documents")
@roles_required("admin")
def documents():

    search_name = request.args.get(
        "search_name", ""
    ).strip()

    search_owner = request.args.get(
        "search_owner", ""
    ).strip()

    search_category = request.args.get(
        "search_category", ""
    ).strip()

    search_date = request.args.get(
        "search_date", ""
    ).strip()

    query = (
        db.session.query(Document, User.full_name)
        .join(User, Document.owner_id == User.id)
    )

    if search_name:
        query = query.filter(
            Document.title.ilike(f"%{search_name}%")
        )

    if search_owner:
        query = query.filter(
            User.full_name.ilike(f"%{search_owner}%")
        )

    if search_category:
        query = query.filter(
            Document.category.ilike(f"%{search_category}%")
        )

    if search_date:
        query = query.filter(
            db.func.date(Document.created_at) == search_date
        )

    documents = (
        query
        .order_by(Document.created_at.desc())
        .all()
    )

    return render_template(
        "admin/documents.html",
        documents=documents,
        search_name=search_name,
        search_owner=search_owner,
        search_category=search_category,
        search_date=search_date
    )
@admin_bp.route("/users")
@roles_required("admin")
def users():
    all_users = User.query.order_by(
        User.created_at.desc()
    ).all()

    return render_template(
        "admin/users.html",
        users=all_users
    )


@admin_bp.route("/users/create", methods=["POST"])
@roles_required("admin")
def create_owner():

    full_name = request.form.get("full_name", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    if not full_name or not email or not password:
        flash("Please fill in all fields.", "error")
        return redirect(url_for("admin.users"))

    if len(full_name) > 120:
        flash("Name must not exceed 120 characters.", "error")
        return redirect(url_for("admin.users"))

    if (
        len(email) > 150
        or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email)
    ):
        flash("Please enter a valid email address.", "error")
        return redirect(url_for("admin.users"))

    if len(password) < 12 or len(password) > 128:
        flash(
            "Password must contain 12 to 128 characters.",
            "error"
        )
        return redirect(url_for("admin.users"))

    existing_user = User.query.filter_by(email=email).first()

    if existing_user:
        flash("An account with this email already exists.", "error")
        return redirect(url_for("admin.users"))

    new_user = User(
        full_name=full_name,
        email=email,
        role="owner",
        is_active=True
    )

    new_user.set_password(password)

    try:
        db.session.add(new_user)
        db.session.flush()

        add_audit_event(
            action="owner_account_created",
            outcome="success",
            details="Administrator created an owner account.",
            target_user_id=new_user.id
        )

        db.session.commit()

        flash("Owner account created successfully.", "success")

    except IntegrityError:
        db.session.rollback()
        flash("This email address is already registered.", "error")

    except Exception:
        db.session.rollback()
        current_app.logger.exception("Owner account creation failed.")
        flash("Could not create the owner account.", "error")

    return redirect(url_for("admin.users"))


@admin_bp.route(
    "/users/<int:user_id>/toggle-status",
    methods=["POST"]
)
@roles_required("admin")
def toggle_user_status(user_id):

    target_user = db.session.get(User, user_id)

    if target_user is None:
        abort(404)

    if target_user.id == current_user.id:
        flash("You cannot change your own account status.", "error")
        return redirect(url_for("admin.users"))

    if target_user.role == "admin" and target_user.is_active:

        active_admin_count = User.query.filter_by(
            role="admin",
            is_active=True
        ).count()

        if active_admin_count <= 1:
            flash(
                "The last active administrator cannot be deactivated.",
                "error"
            )
            return redirect(url_for("admin.users"))

    try:
        target_user.is_active = not target_user.is_active

        if target_user.is_active:
            action = "user_activated"
            details = "Administrator activated a user account."
        else:
            action = "user_deactivated"
            details = "Administrator deactivated a user account."

        add_audit_event(
            action=action,
            outcome="success",
            details=details,
            target_user_id=target_user.id
        )

        db.session.commit()

        flash(
            "User account status updated successfully.",
            "success"
        )

    except Exception:
        db.session.rollback()
        current_app.logger.exception("User status update failed.")
        flash("Could not update the user account status.", "error")

    return redirect(url_for("admin.users"))
@admin_bp.route(
    "/documents/<int:document_id>/delete",
    methods=["POST"]
)
@roles_required("admin")
def admin_delete_document(document_id):
    document = db.session.get(Document, document_id)

    if document is None:
        abort(404)

    if document.deleted_at is not None:
        flash("This document has already been deleted.", "error")
        return redirect(url_for("admin.documents"))

    try:
        document.deleted_at = datetime.utcnow()

        active_permissions = DocumentPermission.query.filter_by(
            document_id=document.id,
            is_active=True
        ).all()

        for permission in active_permissions:
            permission.is_active = False
            permission.revoked_at = datetime.utcnow()

        add_audit_event(
            action="admin_document_delete",
            outcome="success",
            details=(
                "Administrator soft-deleted a document "
                "and revoked active permissions."
            ),
            document_id=document.id
        )

        db.session.commit()

        flash("Document deleted successfully.", "success")

    except Exception:
        db.session.rollback()
        current_app.logger.exception(
            "Administrator document deletion failed."
        )
        flash("Could not delete the document.", "error")

    return redirect(url_for("admin.documents"))