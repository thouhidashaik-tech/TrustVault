# TrustVault — Threat Model

Status: Initial design. Mitigations must be verified through implementation and tests.

## 1. Broken object-level authorisation
Threat: A user changes a document ID in a URL or API request
to access another person's document.
Planned mitigation: Check document-level permission on every
server-side request.
Verification: Cross-user read, download, edit and delete tests.

## 2. Permission revocation failure
Threat: A user continues accessing a document after their
permission has been revoked.
Planned mitigation: Check current database permissions on every
protected request. Do not rely on long-lived access tokens or
cached permission decisions.
Verification: Revoke access and immediately retry all protected routes.

## 3. Insecure direct file access
Threat: Someone guesses or discovers a file URL.
Planned mitigation: Keep uploaded files outside the public static
directory. Serve files only through authorised routes.
Verification: Try direct URL and path traversal attempts.

## 4. Privilege escalation
Threat: A viewer changes a request or form field to become an
administrator or owner.
Planned mitigation: Assign roles on the server; never trust
client-supplied role values.
Verification: Attempt role changes through requests.

## 5. Malicious file upload
Threat: An attacker uploads executable or disguised files.
Planned mitigation: File size limits, extension allowlist,
content validation and random server-side filenames.
Verification: Test invalid extensions, oversized files and
mismatched file contents.

## 6. Audit log tampering
Threat: Someone modifies or deletes evidence of document access.
Planned mitigation: Append-only application behaviour and
cryptographic hash chaining with a separately configured key.
Verification: Modify an audit record and check chain validation.

Known limitation: A hash chain alone cannot prevent a database
administrator from rewriting the entire chain. Stronger
protection would require an independently controlled external
log destination. This limitation must be documented.

## 7. Cross-site request forgery
Threat: A malicious website triggers actions using a logged-in
user's session.
Planned mitigation: CSRF protection for state-changing requests.
Verification: Requests without valid CSRF tokens must fail.

## 8. Session misuse
Threat: An attacker reuses a stolen or improperly managed session.
Planned mitigation: Secure cookie settings, logout and session
protection.
Verification: Check logout and session behaviour.

## 9. SQL injection
Threat: Malicious input changes a database query.
Planned mitigation: SQLAlchemy parameterised queries and
validated input.
Verification: Test suspicious search input.

## 10. Information leakage
Threat: Error messages reveal internal paths, database details
or secrets.
Planned mitigation: Safe error responses and server-side logging.
Verification: Trigger invalid requests and inspect responses.

## 11. Administrator overreach
Threat: An administrator can silently read confidential documents.
Planned mitigation: Administrative access to metadata and audit
information only, unless an explicitly documented need exists.
Verification: Attempt document download as administrator.

## 12. Concurrent permission changes
Threat: A document is accessed while its permission is being revoked.
Planned mitigation: Recheck permission at the point of each
protected operation and use appropriate database transactions.
Verification: Test access immediately after revocation.

## Accepted risks and unfinished protections
To be updated honestly after implementation and testing.