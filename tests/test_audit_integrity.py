
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
