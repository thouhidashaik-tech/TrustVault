
import click
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import User, AuditEvent
from app.audit import add_audit_event


def register_commands(app):

    @app.cli.command("create-user")
    def create_user():
        """Create an administrator, owner or viewer from the terminal."""

        click.echo("\n--- TrustVault User Creation ---")

        full_name = click.prompt("Enter full name").strip()
        email = click.prompt("Enter email").strip().lower()

        role = click.prompt(
            "Select role",
            type=click.Choice(
                ["admin", "owner", "viewer"],
                case_sensitive=False
            )
        ).lower()

        password = click.prompt(
            "Enter password (minimum 12 characters)",
            hide_input=True,
            confirmation_prompt=True
        )

        if not full_name or not email or not password:
            click.echo("Error: All fields are required.")
            return

        if len(password) < 12:
            click.echo("Error: Password must contain at least 12 characters.")
            return

        existing_user = db.session.execute(
            select(User).where(User.email == email)
        ).scalar_one_or_none()

        if existing_user:
            click.echo("Error: This email is already registered.")
            return

        user = User(
            full_name=full_name,
            email=email,
            role=role,
            is_active=True
        )

        user.set_password(password)

        try:
            db.session.add(user)
            db.session.commit()

            click.echo(
                f"\nSuccess! {role} account created for {email}."
            )

        except IntegrityError:
            db.session.rollback()
            click.echo(
                "Error: Could not create account. Check the email."
            )

    @app.cli.command("init-audit-chain")
    def init_audit_chain():
        """Create the initial signed audit-chain event once."""

        existing_genesis = db.session.execute(
            select(AuditEvent).where(
                AuditEvent.action == "audit_chain_genesis"
            )
        ).scalar_one_or_none()

        if existing_genesis:
            click.echo(
                "Audit chain has already been initialized. "
                "No changes were made."
            )
            return

        try:
            add_audit_event(
                action="audit_chain_genesis",
                outcome="success",
                details=(
                    "TrustVault audit-chain verification baseline "
                    "initialized."
                ),
                start_new_chain=True
            )

            db.session.commit()

            click.echo(
                "Success! The audit-chain genesis event was created."
            )

        except Exception:
            db.session.rollback()
            raise click.ClickException(
                "Audit-chain initialization failed. "
                "Check your AUDIT_HMAC_KEY configuration and database."
            )
