
from functools import wraps

from flask import abort, request
from flask_login import current_user, login_required

from app.extensions import db
from app.audit import add_audit_event


def roles_required(*allowed_roles):

    def decorator(view_function):

        @wraps(view_function)
        @login_required
        def wrapped_view(*args, **kwargs):

            if current_user.role not in allowed_roles:

                add_audit_event(
                    action="role_access_denied",
                    outcome="denied",
                    details=(
                        f"User with role '{current_user.role}' "
                        f"was denied access to {request.endpoint}."
                    ),
                    attempted_document_id=kwargs.get("document_id")
                )

                db.session.commit()

                abort(403)

            return view_function(*args, **kwargs)

        return wrapped_view

    return decorator
