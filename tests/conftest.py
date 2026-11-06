import os
import pytest

from app import create_app
from app.extensions import db
from app.models import User, Document, DocumentPermission


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "AUDIT_HMAC_KEY",
        "test-only-secret-key-never-use-in-production"
    )

    application = create_app({
        "TESTING": True,
        "WTF_CSRF_ENABLED": False,
        "SQLALCHEMY_DATABASE_URI": "sqlite://",
        "UPLOAD_FOLDER": str(tmp_path / "uploads"),
        "SECRET_KEY": "test-secret-key"
    })

    os.makedirs(application.config["UPLOAD_FOLDER"], exist_ok=True)

    with application.app_context():
        db.create_all()

        yield application

        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def owner(app):
    with app.app_context():
        user = User(
            full_name="Test Owner",
            email="owner@test.com",
            role="owner",
            is_active=True
        )
        user.set_password("OwnerPassword123!")

        db.session.add(user)
        db.session.commit()

        return user.id


@pytest.fixture
def viewer(app):
    with app.app_context():
        user = User(
            full_name="Test Viewer",
            email="viewer@test.com",
            role="viewer",
            is_active=True
        )
        user.set_password("ViewerPassword123!")

        db.session.add(user)
        db.session.commit()

        return user.id


@pytest.fixture
def document(app, owner):
    with app.app_context():
        doc = Document(
            title="Test Document",
            category="Testing",
            original_filename="test.txt",
            storage_key="test-file-key",
            mime_type="text/plain",
            file_size=25,
            owner_id=owner
        )

        db.session.add(doc)
        db.session.commit()

        return doc.id


@pytest.fixture
def grant_read_permission(app, owner, viewer, document):
    with app.app_context():
        permission = DocumentPermission(
            document_id=document,
            user_id=viewer,
            permission="read",
            granted_by=owner,
            is_active=True
        )

        db.session.add(permission)
        db.session.commit()

        return permission.id


@pytest.fixture
def grant_edit_permission(app, owner, viewer, document):
    with app.app_context():
        permission = DocumentPermission(
            document_id=document,
            user_id=viewer,
            permission="edit",
            granted_by=owner,
            is_active=True
        )

        db.session.add(permission)
        db.session.commit()

        return permission.id


@pytest.fixture
def login_as(client):
    def login(user_id):
        with client.session_transaction() as session:
            session["_user_id"] = str(user_id)
            session["_fresh"] = True

    return login