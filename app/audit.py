
import os
import json
import hmac
import hashlib

from datetime import datetime
from flask import request, has_request_context
from flask_login import current_user

from app.extensions import db
from app.models import AuditEvent


def add_audit_event(
    action,
    outcome,
    details,
    document_id=None,
    target_user_id=None,
    attempted_document_id=None,
    start_new_chain=False,
):
    """
    Add an audit event linked to the previous event.
    The caller is responsible for committing the transaction.
    """

    secret = os.environ.get("AUDIT_HMAC_KEY")

    if not secret:
        raise RuntimeError("AUDIT_HMAC_KEY is not configured.")

    actor_id = None

    if has_request_context() and current_user.is_authenticated:
        actor_id = current_user.id

    ip_address = request.remote_addr if has_request_context() else None

    event = AuditEvent(
        actor_user_id=actor_id,
        document_id=document_id,
        target_user_id=target_user_id,
        attempted_document_id=(
            str(attempted_document_id)
            if attempted_document_id is not None
            else None
        ),
        action=action,
        outcome=outcome,
        details=details,
        ip_address=ip_address,
        timestamp=datetime.utcnow().replace(microsecond=0),
    )

    # Find the most recent audit event.
    previous_event = (
        AuditEvent.query
        .order_by(AuditEvent.id.desc())
        .first()
    )

    if start_new_chain:
        event.previous_hash = None
    else:
        if previous_event and not previous_event.event_hash:
            raise RuntimeError(
            "Cannot extend an unsigned audit chain."
        )

        event.previous_hash = (
            previous_event.event_hash if previous_event else None
    )

    # Obtain the database-generated event ID.
    db.session.add(event)
    db.session.flush()

    # Create a consistent representation of the event.
    event_data = {
        "id": event.id,
        "actor_user_id": event.actor_user_id,
        "document_id": event.document_id,
        "target_user_id": event.target_user_id,
        "attempted_document_id": event.attempted_document_id,
        "action": event.action,
        "outcome": event.outcome,
        "details": event.details,
        "ip_address": event.ip_address,
        "timestamp": event.timestamp.isoformat(),
        "previous_hash": event.previous_hash,
    }

    message = json.dumps(
        event_data,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    event.event_hash = hmac.new(
        secret.encode("utf-8"),
        message,
        hashlib.sha256,
    ).hexdigest()

    return event

def verify_audit_chain():
    """
    Verify all audit records from the first signed event onward.
    Older unsigned records are outside this integrity baseline.
    """

    secret = os.environ.get("AUDIT_HMAC_KEY")

    if not secret:
        return False, "AUDIT_HMAC_KEY is not configured."

    first_signed_event = (
    AuditEvent.query
    .filter(
        AuditEvent.action == "audit_chain_genesis",
        AuditEvent.event_hash.isnot(None)
    )
    .order_by(AuditEvent.id.desc())
    .first()
)

    if first_signed_event is None:
        return False, "No signed audit events were found."

    events = (
        AuditEvent.query
        .filter(AuditEvent.id >= first_signed_event.id)
        .order_by(AuditEvent.id.asc())
        .all()
    )

    previous_hash = None

    for event in events:

        if not event.event_hash:
            return False, f"Unsigned audit event found: ID {event.id}"

        if event.previous_hash != previous_hash:
            return False, f"Previous-hash mismatch at event ID {event.id}"

        event_data = {
            "id": event.id,
            "actor_user_id": event.actor_user_id,
            "document_id": event.document_id,
            "target_user_id": event.target_user_id,
            "attempted_document_id": event.attempted_document_id,
            "action": event.action,
            "outcome": event.outcome,
            "details": event.details,
            "ip_address": event.ip_address,
            "timestamp": event.timestamp.isoformat(),
            "previous_hash": event.previous_hash,
        }

        message = json.dumps(
            event_data,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")

        expected_hash = hmac.new(
            secret.encode("utf-8"),
            message,
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(expected_hash, event.event_hash):
            return False, f"Signature mismatch at event ID {event.id}"

        previous_hash = event.event_hash

    return True, f"Verified {len(events)} signed audit events."
