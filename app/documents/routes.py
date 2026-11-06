
import os
import uuid
from datetime import datetime

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    current_app,
    abort,
    send_file,
)
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from app.models import User, Document, DocumentPermission
from app.extensions import db
from app.permissions import roles_required
from app.audit import add_audit_event


documents_bp = Blueprint(
    "documents",
    __name__,
    url_prefix="/documents"
)


ALLOWED_TYPES = {
    "pdf": ("application/pdf", lambda data: data.startswith(b"%PDF-")),
    "png": ("image/png", lambda data: data.startswith(b"\x89PNG\r\n\x1a\n")),
    "jpg": ("image/jpeg", lambda data: data.startswith(b"\xff\xd8\xff")),
    "jpeg": ("image/jpeg", lambda data: data.startswith(b"\xff\xd8\xff")),
    "txt": ("text/plain", None),
}


def validate_file(uploaded_file, extension):
    uploaded_file.stream.seek(0)
    header = uploaded_file.stream.read(16)
    uploaded_file.stream.seek(0)

    expected_mime, signature_check = ALLOWED_TYPES[extension]

    if signature_check:
        return signature_check(header), expected_mime

    try:
        uploaded_file.stream.seek(0)
        uploaded_file.stream.read().decode("utf-8")
        uploaded_file.stream.seek(0)
        return True, expected_mime
    except UnicodeDecodeError:
        uploaded_file.stream.seek(0)
        return False, expected_mime


def record_download_attempt(document, document_id, outcome, details):
    add_audit_event(
        action="download",
        outcome=outcome,
        details=details,
        document_id=document.id if document else None,
        attempted_document_id=document_id
    )

    db.session.commit()


@documents_bp.route("/dashboard")
@roles_required("owner")
def dashboard():

    search_name = request.args.get("search_name", "").strip()
    search_category = request.args.get("search_category", "").strip()
    search_date = request.args.get("search_date", "").strip()

    query = Document.query.filter(
        Document.owner_id == current_user.id,
        Document.deleted_at.is_(None)
    )

    if search_name:
        query = query.filter(
            Document.title.ilike(f"%{search_name}%")
        )

    if search_category:
        query = query.filter(
            Document.category.ilike(f"%{search_category}%")
        )

    if search_date:
        query = query.filter(
            db.func.date(Document.created_at) == search_date
        )

    documents = query.order_by(
        Document.created_at.desc()
    ).all()

    return render_template(
        "documents/dashboard.html",
        documents=documents
    )


@documents_bp.route("/upload", methods=["POST"])
@roles_required("owner")
def upload():

    title = request.form.get("title", "").strip()
    category = request.form.get("category", "").strip()
    uploaded_file = request.files.get("document_file")

    if not title or not category or not uploaded_file:
        flash("Please fill in all fields and select a file.", "error")
        return redirect(url_for("documents.dashboard"))

    if not uploaded_file.filename:
        flash("Please select a file.", "error")
        return redirect(url_for("documents.dashboard"))

    safe_filename = secure_filename(uploaded_file.filename)

    if not safe_filename or "." not in safe_filename:
        flash("Invalid filename.", "error")
        return redirect(url_for("documents.dashboard"))

    extension = safe_filename.rsplit(".", 1)[1].lower()

    if extension not in ALLOWED_TYPES:
        flash("File type not allowed.", "error")
        return redirect(url_for("documents.dashboard"))

    is_valid, detected_mime = validate_file(
        uploaded_file,
        extension
    )

    if not is_valid:
        flash("The file content does not match its file type.", "error")
        return redirect(url_for("documents.dashboard"))

    uploaded_file.stream.seek(0, os.SEEK_END)
    file_size = uploaded_file.stream.tell()
    uploaded_file.stream.seek(0)

    if file_size == 0:
        flash("Empty files cannot be uploaded.", "error")
        return redirect(url_for("documents.dashboard"))

    if file_size > current_app.config["MAX_CONTENT_LENGTH"]:
        flash("File is too large. Maximum size is 16 MB.", "error")
        return redirect(url_for("documents.dashboard"))

    storage_key = str(uuid.uuid4())

    upload_folder = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(upload_folder, exist_ok=True)

    file_path = os.path.join(upload_folder, storage_key)

    document = Document(
        title=title,
        category=category,
        original_filename=safe_filename,
        storage_key=storage_key,
        mime_type=detected_mime,
        file_size=file_size,
        owner_id=current_user.id
    )

    try:
        uploaded_file.save(file_path)

        db.session.add(document)
        db.session.flush()

        add_audit_event(
            action="upload",
            outcome="success",
            details="Document uploaded successfully.",
            document_id=document.id
        )

        db.session.commit()

    except Exception:
        db.session.rollback()

        if os.path.exists(file_path):
            os.remove(file_path)

        current_app.logger.exception("Document upload failed.")
        flash("Upload failed. Please try again.", "error")
        return redirect(url_for("documents.dashboard"))

    flash("Document uploaded successfully!", "success")
    return redirect(url_for("documents.dashboard"))


@documents_bp.route("/download/<int:document_id>")
@login_required
def download(document_id):

    document = db.session.get(Document, document_id)

    if document is not None and document.deleted_at is not None:
        record_download_attempt(
            document,
            document_id,
            "denied",
            "Attempted to download a deleted document."
        )
        abort(404)

    is_owner = (
        document is not None
        and document.owner_id == current_user.id
    )

    permission = None

    if document is not None and not is_owner:
        permission = DocumentPermission.query.filter(
            DocumentPermission.document_id == document.id,
            DocumentPermission.user_id == current_user.id,
            DocumentPermission.is_active.is_(True),
            DocumentPermission.permission.in_(["read", "edit"])
        ).first()

    has_access = is_owner or permission is not None

    if not has_access:
        record_download_attempt(
            document,
            document_id,
            "denied",
            "Download refused: user does not have document permission."
        )
        abort(404)

    file_path = os.path.join(
        current_app.config["UPLOAD_FOLDER"],
        document.storage_key
    )

    if not os.path.isfile(file_path):
        record_download_attempt(
            document,
            document_id,
            "denied",
            "Download refused: stored file is missing."
        )
        abort(404)

    record_download_attempt(
        document,
        document_id,
        "success",
        "Document downloaded successfully."
    )

    return send_file(
        file_path,
        as_attachment=True,
        download_name=document.original_filename,
        mimetype="application/octet-stream"
    )


@documents_bp.route("/share/<int:document_id>", methods=["POST"])
@roles_required("owner")
def share_document(document_id):

    document = db.session.get(Document, document_id)

    if (
        document is None
        or document.deleted_at is not None
        or document.owner_id != current_user.id
    ):
        add_audit_event(
            action="permission_grant",
            outcome="denied",
            details="Unauthorized attempt to share a document.",
            document_id=document.id if document else None,
            attempted_document_id=document_id
        )
        db.session.commit()
        abort(404)

    email = request.form.get("email", "").strip().lower()
    permission_type = request.form.get("permission", "").strip().lower()

    if not email or permission_type not in ("read", "edit"):
        flash("Please provide a valid email and permission.", "error")
        return redirect(url_for("documents.dashboard"))

    target_user = User.query.filter_by(email=email).first()

    if target_user is None:
        flash("No registered user found with that email.", "error")
        return redirect(url_for("documents.dashboard"))

    if target_user.id == current_user.id:
        flash("You already own this document.", "error")
        return redirect(url_for("documents.dashboard"))

    existing_permission = DocumentPermission.query.filter_by(
        document_id=document.id,
        user_id=target_user.id
    ).first()

    try:
        if existing_permission:
            existing_permission.permission = permission_type
            existing_permission.granted_by = current_user.id
            existing_permission.is_active = True
            existing_permission.revoked_at = None

        else:
            new_permission = DocumentPermission(
                document_id=document.id,
                user_id=target_user.id,
                permission=permission_type,
                granted_by=current_user.id,
                is_active=True
            )
            db.session.add(new_permission)

        add_audit_event(
            action="permission_grant",
            outcome="success",
            details=f"Granted {permission_type} permission.",
            document_id=document.id,
            target_user_id=target_user.id
        )

        db.session.commit()

        flash(
            f"{permission_type.title()} permission granted successfully!",
            "success"
        )

    except Exception:
        db.session.rollback()
        current_app.logger.exception("Permission grant failed.")
        flash("Could not share the document. Please try again.", "error")

    return redirect(url_for("documents.dashboard"))


@documents_bp.route(
    "/revoke/<int:document_id>/<int:user_id>",
    methods=["POST"]
)
@roles_required("owner")
def revoke_permission(document_id, user_id):

    document = db.session.get(Document, document_id)

    if (
        document is None
        or document.deleted_at is not None
        or document.owner_id != current_user.id
    ):
        add_audit_event(
            action="permission_revoke",
            outcome="denied",
            details="Unauthorized attempt to revoke document permission.",
            document_id=document.id if document else None,
            attempted_document_id=document_id,
            target_user_id=user_id
        )
        db.session.commit()
        abort(404)

    permission = DocumentPermission.query.filter_by(
        document_id=document.id,
        user_id=user_id,
        is_active=True
    ).first()

    if permission is None:
        flash("No active permission found for this user.", "error")
        return redirect(url_for("documents.dashboard"))

    try:
        permission.is_active = False
        permission.revoked_at = datetime.utcnow()

        add_audit_event(
            action="permission_revoke",
            outcome="success",
            details="Document permission revoked.",
            document_id=document.id,
            target_user_id=user_id
        )

        db.session.commit()

        flash("Document access revoked successfully!", "success")

    except Exception:
        db.session.rollback()
        current_app.logger.exception("Permission revocation failed.")
        flash("Could not revoke permission. Please try again.", "error")

    return redirect(url_for("documents.dashboard"))


@documents_bp.route("/shared")
@roles_required("viewer")
def shared_documents():

    shared_documents = (
        Document.query
        .join(
            DocumentPermission,
            DocumentPermission.document_id == Document.id
        )
        .filter(
            DocumentPermission.user_id == current_user.id,
            DocumentPermission.is_active.is_(True),
            Document.deleted_at.is_(None)
        )
        .order_by(Document.created_at.desc())
        .all()
    )

    return render_template(
        "documents/shared.html",
        documents=shared_documents
    )


@documents_bp.route("/edit/<int:document_id>", methods=["GET", "POST"])
@login_required
def edit_document(document_id):

    document = db.session.get(Document, document_id)

    if document is not None and document.deleted_at is not None:
        add_audit_event(
            action="edit",
            outcome="denied",
            details="Attempted to edit a deleted document.",
            document_id=document.id,
            attempted_document_id=document_id
        )
        db.session.commit()
        abort(404)

    is_owner = (
        document is not None
        and document.owner_id == current_user.id
    )

    edit_permission = None

    if document is not None and not is_owner:
        edit_permission = DocumentPermission.query.filter(
            DocumentPermission.document_id == document.id,
            DocumentPermission.user_id == current_user.id,
            DocumentPermission.permission == "edit",
            DocumentPermission.is_active.is_(True)
        ).first()

    has_edit_access = is_owner or edit_permission is not None

    if not has_edit_access:
        add_audit_event(
            action="edit",
            outcome="denied",
            details="Edit refused: user does not have edit permission.",
            document_id=document.id if document else None,
            attempted_document_id=document_id
        )
        db.session.commit()
        abort(404)

    if request.method == "POST":

        title = request.form.get("title", "").strip()
        category = request.form.get("category", "").strip()
        description = request.form.get("description", "").strip()

        if not title or not category:
            flash("Title and category are required.", "error")
            return redirect(
                url_for(
                    "documents.edit_document",
                    document_id=document.id
                )
            )

        if len(title) > 200 or len(category) > 100:
            flash("Title or category is too long.", "error")
            return redirect(
                url_for(
                    "documents.edit_document",
                    document_id=document.id
                )
            )

        try:
            document.title = title
            document.category = category
            document.description = description

            add_audit_event(
                action="edit",
                outcome="success",
                details="Document details updated.",
                document_id=document.id
            )

            db.session.commit()
            flash("Document updated successfully!", "success")

        except Exception:
            db.session.rollback()
            current_app.logger.exception("Document edit failed.")
            flash("Could not update the document.", "error")

        if is_owner:
            return redirect(url_for("documents.dashboard"))

        return redirect(url_for("documents.shared_documents"))

    return render_template(
        "documents/edit.html",
        document=document
    )


@documents_bp.route("/delete/<int:document_id>", methods=["POST"])
@roles_required("owner")
def delete_document(document_id):

    document = db.session.get(Document, document_id)

    if (
        document is None
        or document.deleted_at is not None
        or document.owner_id != current_user.id
    ):
        add_audit_event(
            action="delete",
            outcome="denied",
            details="Unauthorized document deletion attempt.",
            document_id=document.id if document else None,
            attempted_document_id=document_id
        )
        db.session.commit()
        abort(404)

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
            action="delete",
            outcome="success",
            details="Document soft-deleted and active permissions revoked.",
            document_id=document.id
        )

        db.session.commit()

        flash("Document deleted successfully.", "success")

    except Exception:
        db.session.rollback()
        current_app.logger.exception("Document deletion failed.")
        flash("Could not delete the document.", "error")

    return redirect(url_for("documents.dashboard"))
