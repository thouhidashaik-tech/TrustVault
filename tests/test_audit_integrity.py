import pytest
from app.extensions import db
from app.models import AuditEvent
from app.audit import add_audit_event, verify_audit_chain


def test_audit_chain_verifies_successfully(app):
    with app.app_context():
        add_audit_event(
            action="audit_chain_genesis",
            outcome="success",
            details="Test audit chain started",
            start_new_chain=True
        )
        db.session.commit()

        add_audit_event(
            action="document_download",
            outcome="success",
            details="Test document downloaded"
        )
        db.session.commit()

        valid, message = verify_audit_chain()

        assert valid is True
        assert "Verified" in message


def test_audit_chain_detects_tampering(app):
    with app.app_context():
        add_audit_event(
            action="audit_chain_genesis",
            outcome="success",
            details="Test audit chain started",
            start_new_chain=True
        )
        db.session.commit()

        add_audit_event(
            action="document_download",
            outcome="success",
            details="Original audit details"
        )
        db.session.commit()

        event = (
            AuditEvent.query
            .filter_by(action="document_download")
            .first()
        )

        event.details = "Tampered audit details"
        db.session.commit()

        valid, message = verify_audit_chain()

        assert valid is False
        assert "Signature mismatch" in message


def test_audit_chain_detects_missing_signature(app):
    with app.app_context():
        add_audit_event(
            action="audit_chain_genesis",
            outcome="success",
            details="Test audit chain started",
            start_new_chain=True
        )
        db.session.commit()

        add_audit_event(
            action="document_download",
            outcome="success",
            details="Test document downloaded"
        )
        db.session.commit()

        event = (
            AuditEvent.query
            .filter_by(action="document_download")
            .first()
        )

        event.event_hash = None
        db.session.commit()

        valid, message = verify_audit_chain()

        assert valid is False
        assert "Unsigned audit event" in message
def test_audit_chain_rejects_second_genesis(app):
    with app.app_context():
        add_audit_event(
            action="audit_chain_genesis",
            outcome="success",
            details="First baseline",
            start_new_chain=True
        )
        db.session.commit()

        with pytest.raises(RuntimeError, match="already exists"):
            add_audit_event(
                action="audit_chain_genesis",
                outcome="success",
                details="Second baseline",
                start_new_chain=True
            )

        db.session.rollback()


def test_audit_chain_detects_deleted_middle_event(app):
    with app.app_context():
        add_audit_event(
            action="audit_chain_genesis",
            outcome="success",
            details="Test baseline",
            start_new_chain=True
        )
        db.session.commit()

        add_audit_event(
            action="document_download",
            outcome="success",
            details="First event"
        )
        db.session.commit()

        middle = add_audit_event(
            action="document_download",
            outcome="success",
            details="Middle event"
        )
        db.session.commit()

        add_audit_event(
            action="document_download",
            outcome="success",
            details="Last event"
        )
        db.session.commit()

        db.session.delete(middle)
        db.session.commit()

        valid, message = verify_audit_chain()

        assert valid is False
        assert "Previous-hash mismatch" in message