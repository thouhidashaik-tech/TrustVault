import os
from io import BytesIO
from app.extensions import db
from app.models import Document, DocumentPermission, AuditEvent
from app.models import User, Document, DocumentPermission, AuditEvent
from datetime import datetime

def create_test_file(app):
    path = os.path.join(
        app.config["UPLOAD_FOLDER"],
        "test-file-key"
    )

    with open(path, "w", encoding="utf-8") as file:
        file.write("This is a test document.")

    return path

def test_private_document_denies_viewer(
    app, client, viewer, document, login_as
):
    login_as(viewer)

    response = client.get(
        f"/documents/download/{document}"
    )

    assert response.status_code == 404

    with app.app_context():
        event = AuditEvent.query.filter_by(
            action="download",
            outcome="denied"
        ).first()

        assert event is not None

def test_read_permission_allows_download(
    app, client, viewer, document,
    grant_read_permission, login_as
):
    create_test_file(app)
    login_as(viewer)

    response = client.get(
        f"/documents/download/{document}"
    )

    assert response.status_code == 200
    assert b"This is a test document." in response.data

def test_read_permission_denies_edit(
    client, viewer, document,
    grant_read_permission, login_as
):
    login_as(viewer)

    response = client.get(
        f"/documents/edit/{document}"
    )

    assert response.status_code == 404

def test_edit_permission_allows_edit(
    client, viewer, document,
    grant_edit_permission, login_as
):
    login_as(viewer)

    response = client.post(
        f"/documents/edit/{document}",
        data={
            "title": "Updated Test Document",
            "category": "Testing",
            "description": "Updated by authorized viewer"
        },
        follow_redirects=False
    )

    assert response.status_code == 302

def test_viewer_cannot_delete_document(
    client, viewer, document, login_as
):
    login_as(viewer)

    response = client.post(
        f"/documents/delete/{document}"
    )

    assert response.status_code == 403

def test_revoked_permission_denies_download(
    app, client, viewer, document,
    grant_read_permission, login_as
):
    with app.app_context():
        permission = DocumentPermission.query.filter_by(
            document_id=document,
            user_id=viewer
        ).first()

        permission.is_active = False
        db.session.commit()

    login_as(viewer)

    response = client.get(
        f"/documents/download/{document}"
    )

    assert response.status_code == 404

def test_owner_can_download_own_document(
    app, client, owner, document, login_as
):
    create_test_file(app)
    login_as(owner)

    response = client.get(
        f"/documents/download/{document}"
    )

    assert response.status_code == 200

def test_viewer_cannot_share_document_and_attempt_is_audited(
    app, client, viewer, document, login_as
):
    login_as(viewer)

    response = client.post(
        f"/documents/share/{document}",
        data={
            "email": "another@test.com",
            "permission": "read"
        }
    )

    assert response.status_code == 403

    with app.app_context():
        event = AuditEvent.query.filter_by(
            action="role_access_denied",
            outcome="denied",
            attempted_document_id=str(document)
        ).first()

        assert event is not None

def test_viewer_cannot_revoke_permission_and_attempt_is_audited(
    app, client, viewer, document, login_as
):
    login_as(viewer)

    response = client.post(
        f"/documents/revoke/{document}/999"
    )

    assert response.status_code == 403

    with app.app_context():
        event = AuditEvent.query.filter_by(
            action="role_access_denied",
            outcome="denied",
            attempted_document_id=str(document)
        ).first()

        assert event is not None
def test_deleted_document_cannot_be_downloaded(
    app, client, owner, viewer, document,
    grant_read_permission, login_as
):
    from datetime import datetime
    from app.models import Document, AuditEvent
    from app.extensions import db

    with app.app_context():
        doc = db.session.get(Document, document)
        doc.deleted_at = datetime.utcnow()
        db.session.commit()

    login_as(viewer)

    response = client.get(
        f"/documents/download/{document}"
    )

    assert response.status_code == 404

    with app.app_context():
        event = AuditEvent.query.filter_by(
            action="download",
            outcome="denied",
            attempted_document_id=str(document)
        ).first()

        assert event is not None
        assert "deleted" in event.details.lower()
def test_upload_rejects_unsupported_file_extension(
    app, client, owner, login_as
):
    login_as(owner)

    with app.app_context():
        initial_count = Document.query.count()

    response = client.post(
        "/documents/upload",
        data={
            "title": "Invalid File",
            "category": "Testing",
            "document_file": (
                BytesIO(b"sample content"),
                "malware.exe"
            )
        },
        content_type="multipart/form-data"
    )

    assert response.status_code == 302

    with app.app_context():
        assert Document.query.count() == initial_count


def test_upload_rejects_fake_pdf_file(
    app, client, owner, login_as
):
    login_as(owner)

    with app.app_context():
        initial_count = Document.query.count()

    response = client.post(
        "/documents/upload",
        data={
            "title": "Fake PDF",
            "category": "Testing",
            "document_file": (
                BytesIO(b"This is not a real PDF file"),
                "fake.pdf"
            )
        },
        content_type="multipart/form-data"
    )

    assert response.status_code == 302

    with app.app_context():
        assert Document.query.count() == initial_count


def test_upload_rejects_empty_file(
    app, client, owner, login_as
):
    login_as(owner)

    with app.app_context():
        initial_count = Document.query.count()

    response = client.post(
        "/documents/upload",
        data={
            "title": "Empty File",
            "category": "Testing",
            "document_file": (
                BytesIO(b""),
                "empty.txt"
            )
        },
        content_type="multipart/form-data"
    )

    assert response.status_code == 302

    with app.app_context():
        assert Document.query.count() == initial_count
def test_another_owner_cannot_access_or_delete_document(
    app, client, document, login_as
):
    with app.app_context():
        another_owner = User(
            full_name="Another Owner",
            email="anotherowner@test.com",
            role="owner",
            is_active=True
        )
        another_owner.set_password("AnotherOwner123!")

        db.session.add(another_owner)
        db.session.commit()

        another_owner_id = another_owner.id

    login_as(another_owner_id)

    # Attempt to download another owner's document
    download_response = client.get(
        f"/documents/download/{document}"
    )
    assert download_response.status_code == 404

    # Attempt to edit another owner's document
    edit_response = client.get(
        f"/documents/edit/{document}"
    )
    assert edit_response.status_code == 404

    # Attempt to delete another owner's document
    delete_response = client.post(
        f"/documents/delete/{document}"
    )
    assert delete_response.status_code == 404

    with app.app_context():
        assert AuditEvent.query.filter_by(
            action="download",
            outcome="denied"
        ).count() >= 1

        assert AuditEvent.query.filter_by(
            action="edit",
            outcome="denied"
        ).count() >= 1

        assert AuditEvent.query.filter_by(
            action="delete",
            outcome="denied"
        ).count() >= 1

def test_unauthenticated_user_cannot_download(
    client, document
):
    response = client.get(
        f"/documents/download/{document}"
    )
    assert response.status_code == 302


def test_unauthenticated_user_cannot_edit(
    client, document
):
    response = client.get(
        f"/documents/edit/{document}"
    )
    assert response.status_code == 302


def test_unauthenticated_user_cannot_upload(client):
    response = client.post(
        "/documents/upload"
    )
    assert response.status_code == 302


def test_unauthenticated_user_cannot_access_owner_dashboard(
    client
):
    response = client.get("/documents/dashboard")
    assert response.status_code == 302


def test_viewer_cannot_access_owner_dashboard(
    client, viewer, login_as
):
    login_as(viewer)

    response = client.get("/documents/dashboard")

    assert response.status_code == 403


def test_admin_cannot_download_private_document(
    app, client, document, login_as
):
    with app.app_context():
        admin = User(
            full_name="Test Admin",
            email="admin-security@test.com",
            role="admin",
            is_active=True
        )
        admin.set_password("AdminPassword123!")

        db.session.add(admin)
        db.session.commit()

        admin_id = admin.id

    login_as(admin_id)

    response = client.get(
        f"/documents/download/{document}"
    )

    assert response.status_code == 404


def test_owner_cannot_share_deleted_document(
    app, client, owner, document, login_as
):
    with app.app_context():
        doc = db.session.get(Document, document)
        doc.deleted_at = datetime.utcnow()
        db.session.commit()

    login_as(owner)

    response = client.post(
        f"/documents/share/{document}",
        data={
            "email": "viewer@test.com",
            "permission": "read"
        }
    )

    assert response.status_code == 404


def test_owner_cannot_edit_deleted_document(
    app, client, owner, document, login_as
):
    with app.app_context():
        doc = db.session.get(Document, document)
        doc.deleted_at = datetime.utcnow()
        db.session.commit()

    login_as(owner)

    response = client.get(
        f"/documents/edit/{document}"
    )

    assert response.status_code == 404


def test_owner_cannot_delete_already_deleted_document(
    app, client, owner, document, login_as
):
    with app.app_context():
        doc = db.session.get(Document, document)
        doc.deleted_at = datetime.utcnow()
        db.session.commit()

    login_as(owner)

    response = client.post(
        f"/documents/delete/{document}"
    )

    assert response.status_code == 404

def test_owner_can_upload_valid_text_document(
    app, client, owner, login_as
):
    login_as(owner)

    response = client.post(
        "/documents/upload",
        data={
            "title": "Security Test Document",
            "category": "Testing",
            "document_file": (
                BytesIO(b"Valid document content"),
                "security_test.txt"
            )
        },
        content_type="multipart/form-data"
    )

    assert response.status_code == 302

    with app.app_context():
        doc = Document.query.filter_by(
            title="Security Test Document"
        ).first()

        assert doc is not None

        file_path = os.path.join(
            app.config["UPLOAD_FOLDER"],
            doc.storage_key
        )

        assert os.path.isfile(file_path)

        event = AuditEvent.query.filter_by(
            action="upload",
            outcome="success",
            document_id=doc.id
        ).first()

        assert event is not None


def test_owner_can_grant_read_permission(
    app, client, owner, viewer, document, login_as
):
    login_as(owner)

    response = client.post(
        f"/documents/share/{document}",
        data={
            "email": "viewer@test.com",
            "permission": "read"
        }
    )

    assert response.status_code == 302

    with app.app_context():
        permission = DocumentPermission.query.filter_by(
            document_id=document,
            user_id=viewer,
            is_active=True
        ).first()

        assert permission is not None
        assert permission.permission == "read"

        event = AuditEvent.query.filter_by(
            action="permission_grant",
            outcome="success",
            document_id=document,
            target_user_id=viewer
        ).first()

        assert event is not None


def test_owner_can_revoke_active_permission(
    app, client, owner, viewer, document,
    grant_read_permission, login_as
):
    login_as(owner)

    response = client.post(
        f"/documents/revoke/{document}/{viewer}"
    )

    assert response.status_code == 302

    with app.app_context():
        permission = DocumentPermission.query.filter_by(
            document_id=document,
            user_id=viewer
        ).first()

        assert permission is not None
        assert permission.is_active is False
        assert permission.revoked_at is not None

        event = AuditEvent.query.filter_by(
            action="permission_revoke",
            outcome="success",
            document_id=document,
            target_user_id=viewer
        ).first()

        assert event is not None


def test_owner_can_delete_document_and_revoke_permissions(
    app, client, owner, viewer, document,
    grant_read_permission, login_as
):
    login_as(owner)

    response = client.post(
        f"/documents/delete/{document}"
    )

    assert response.status_code == 302

    with app.app_context():
        doc = db.session.get(Document, document)

        assert doc.deleted_at is not None

        permission = DocumentPermission.query.filter_by(
            document_id=document,
            user_id=viewer
        ).first()

        assert permission.is_active is False
        assert permission.revoked_at is not None

        event = AuditEvent.query.filter_by(
            action="delete",
            outcome="success",
            document_id=document
        ).first()

        assert event is not None


def test_nonexistent_document_download_is_audited(
    app, client, owner, login_as
):
    login_as(owner)

    response = client.get(
        "/documents/download/999999"
    )

    assert response.status_code == 404

    with app.app_context():
        event = AuditEvent.query.filter_by(
            action="download",
            outcome="denied",
            attempted_document_id="999999"
        ).first()

        assert event is not None


def test_nonexistent_document_edit_is_audited(
    app, client, owner, login_as
):
    login_as(owner)

    response = client.get(
        "/documents/edit/999999"
    )

    assert response.status_code == 404

    with app.app_context():
        event = AuditEvent.query.filter_by(
            action="edit",
            outcome="denied",
            attempted_document_id="999999"
        ).first()

        assert event is not None

def test_owner_cannot_access_viewer_shared_documents(
    client, owner, login_as
):
    login_as(owner)

    response = client.get("/documents/shared")

    assert response.status_code == 403


def test_viewer_cannot_access_admin_dashboard(
    client, viewer, login_as
):
    login_as(viewer)

    response = client.get("/admin/dashboard")

    assert response.status_code == 403


def test_owner_cannot_access_admin_activity(
    client, owner, login_as
):
    login_as(owner)

    response = client.get("/admin/activity")

    assert response.status_code == 403


def test_admin_cannot_access_owner_dashboard(
    app, client, login_as
):
    with app.app_context():
        admin = User(
            full_name="Security Admin",
            email="securityadmin@test.com",
            role="admin",
            is_active=True
        )
        admin.set_password("SecurityAdmin123!")

        db.session.add(admin)
        db.session.commit()

        admin_id = admin.id

    login_as(admin_id)

    response = client.get("/documents/dashboard")

    assert response.status_code == 403


def test_read_permission_cannot_modify_document(
    app, client, viewer, document,
    grant_read_permission, login_as
):
    login_as(viewer)

    response = client.post(
        f"/documents/edit/{document}",
        data={
            "title": "Unauthorized Modification",
            "category": "Changed",
            "description": "This should not be saved"
        }
    )

    assert response.status_code == 404

    with app.app_context():
        doc = db.session.get(Document, document)

        assert doc.title == "Test Document"
        assert doc.category == "Testing"


def test_owner_cannot_share_another_owners_document(
    app, client, owner, viewer, login_as
):
    with app.app_context():
        another_owner = User(
            full_name="Different Owner",
            email="differentowner@test.com",
            role="owner",
            is_active=True
        )
        another_owner.set_password("DifferentOwner123!")

        db.session.add(another_owner)
        db.session.commit()

        other_doc = Document(
            title="Private Document",
            category="Confidential",
            original_filename="private.txt",
            storage_key="private-test-key",
            mime_type="text/plain",
            file_size=20,
            owner_id=another_owner.id
        )

        db.session.add(other_doc)
        db.session.commit()

        other_document_id = other_doc.id

    login_as(owner)

    response = client.post(
        f"/documents/share/{other_document_id}",
        data={
            "email": "viewer@test.com",
            "permission": "read"
        }
    )

    assert response.status_code == 404

    with app.app_context():
        event = AuditEvent.query.filter_by(
            action="permission_grant",
            outcome="denied",
            attempted_document_id=str(other_document_id)
        ).first()

        assert event is not None
