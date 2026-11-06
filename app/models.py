
from datetime import datetime
import uuid

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from app.extensions import db, login_manager


# Use the same MySQL BIGINT type for every foreign key
# that references users.id.
USER_ID_TYPE = db.BigInteger().with_variant(db.Integer, "sqlite")


# 1. USER MODEL
class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(
        USER_ID_TYPE,
        primary_key=True
    )

    full_name = db.Column(
        db.String(120),
        nullable=False
    )

    email = db.Column(
        db.String(150),
        unique=True,
        nullable=False,
        index=True
    )

    password_hash = db.Column(
        db.String(255),
        nullable=False
    )

    role = db.Column(
        db.String(20),
        nullable=False,
        default="viewer"
    )

    is_active = db.Column(
        db.Boolean,
        nullable=False,
        default=True
    )

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow
    )

    owned_documents = db.relationship(
        "Document",
        backref="owner",
        lazy=True,
        foreign_keys="Document.owner_id"
    )

    permissions = db.relationship(
        "DocumentPermission",
        backref="user",
        lazy=True,
        foreign_keys="DocumentPermission.user_id"
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


# 2. DOCUMENT MODEL
class Document(db.Model):
    __tablename__ = "documents"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    title = db.Column(
        db.String(200),
        nullable=False
    )

    category = db.Column(
        db.String(100),
        nullable=False
    )

    description = db.Column(
        db.Text,
        nullable=True
    )

    original_filename = db.Column(
        db.String(255),
        nullable=False
    )

    storage_key = db.Column(
        db.String(36),
        unique=True,
        nullable=False,
        default=lambda: str(uuid.uuid4())
    )

    mime_type = db.Column(
        db.String(100),
        nullable=False
    )

    file_size = db.Column(
        db.BigInteger,
        nullable=False
    )

    owner_id = db.Column(
        USER_ID_TYPE,
        db.ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow
    )

    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    deleted_at = db.Column(
        db.DateTime,
        nullable=True
    )

    permissions = db.relationship(
        "DocumentPermission",
        backref="document",
        lazy=True,
        cascade="all, delete-orphan"
    )


# 3. DOCUMENT PERMISSION MODEL
class DocumentPermission(db.Model):
    __tablename__ = "document_permissions"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    document_id = db.Column(
        db.Integer,
        db.ForeignKey("documents.id"),
        nullable=False
    )

    user_id = db.Column(
        USER_ID_TYPE,
        db.ForeignKey("users.id"),
        nullable=False
    )

    permission = db.Column(
        db.String(10),
        nullable=False
    )

    granted_by = db.Column(
        USER_ID_TYPE,
        db.ForeignKey("users.id"),
        nullable=False
    )

    is_active = db.Column(
        db.Boolean,
        nullable=False,
        default=True
    )

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow
    )

    revoked_at = db.Column(
        db.DateTime,
        nullable=True
    )

    __table_args__ = (
        db.UniqueConstraint(
            "document_id",
            "user_id",
            name="unique_document_user_permission"
        ),
        db.CheckConstraint(
            "permission IN ('read', 'edit')",
            name="valid_document_permission"
        ),
    )


# 4. AUDIT EVENT MODEL
class AuditEvent(db.Model):
    __tablename__ = "audit_events"

    id = db.Column(
        db.BigInteger().with_variant(db.Integer, "sqlite"),
        primary_key=True
    )

    actor_user_id = db.Column(
        USER_ID_TYPE,
        db.ForeignKey("users.id"),
        nullable=True
    )

    document_id = db.Column(
        db.Integer,
        db.ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True
    )

    action = db.Column(
        db.String(50),
        nullable=False
    )

    outcome = db.Column(
        db.String(10),
        nullable=False
    )

    target_user_id = db.Column(
        USER_ID_TYPE,
        db.ForeignKey("users.id"),
        nullable=True
    )

    attempted_document_id = db.Column(
        db.String(100),
        nullable=True
    )

    details = db.Column(
        db.Text,
        nullable=True
    )

    ip_address = db.Column(
        db.String(45),
        nullable=True
    )

    timestamp = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True
    )

    previous_hash = db.Column(
        db.String(64),
        nullable=True
    )

    event_hash = db.Column(
        db.String(64),
        nullable=True
    )

    __table_args__ = (
        db.CheckConstraint(
            "outcome IN ('success', 'denied')",
            name="valid_audit_outcome"
        ),
    )


# 5. USER LOADER
@login_manager.user_loader
def load_user(user_id):
    try:
        return db.session.get(User, int(user_id))
    except (ValueError, TypeError):
        return None
