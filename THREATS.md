# TrustVault — Threat Model

**Project:** TrustVault  
**Last updated:** November 7, 2026  
**Status:** Implemented protections are covered by application code and automated tests. Production security still requires deployment verification.

## 1. Broken Object-Level Authorization

**Threat:** A user changes a document ID in a URL or request to access another user's document.

**Implemented mitigation:** Document ownership and active document-level permissions are checked on protected server-side routes.

**Verification:** Automated tests cover unauthorized document access and protected operations.

## 2. Permission Revocation Failure

**Threat:** A user continues accessing a document after their permission is revoked.

**Implemented mitigation:** Current database permissions are checked when protected operations are requested rather than relying on cached permission decisions.

**Verification:** Permission revocation and access-control tests are included in the test suite.

## 3. Insecure Direct File Access

**Threat:** Someone guesses or discovers a document URL or storage path.

**Implemented mitigation:** Uploaded files are stored in a private directory outside the public static directory. Downloads use protected application routes.

**Verification:** Download authorization is checked server-side.

## 4. Privilege Escalation

**Threat:** A viewer changes request data to become an administrator or owner.

**Implemented mitigation:** Roles are assigned and checked server-side. Client-supplied role values are not trusted for authorization.

**Verification:** Role-based route tests cover protected operations.

## 5. Malicious File Upload

**Threat:** An attacker uploads executable, disguised, empty or oversized files.

**Implemented mitigation:** Upload validation includes an extension allowlist, content validation, filename sanitization, random server-side filenames and a 16 MB application upload limit.

**Verification:** Upload validation tests cover invalid upload scenarios.

## 6. Audit Log Tampering

**Threat:** Someone modifies audit records to hide document activity.

**Implemented mitigation:** Audit events are linked using previous hashes and HMAC-SHA256 signatures. The signing key is configured separately through `AUDIT_HMAC_KEY`. Verification checks signatures and chain continuity. The application prevents normal audit-chain initialization from creating a second genesis event.

**Verification:** Automated tests cover valid chains, modified records, missing signatures, second genesis attempts and deletion of a middle event.

**Known limitations:**
- A database administrator with access to both the database and HMAC secret may be able to rewrite the chain.
- Deletion of the final event cannot be detected by a hash chain without an independently stored checkpoint.
- Older unsigned records before the signed genesis event are outside the verification baseline.
- The HMAC secret must be protected independently of the database.

**Future improvement:** Send audit events or periodic chain checkpoints to an independently controlled logging service.

## 7. Cross-Site Request Forgery

**Threat:** A malicious website attempts to perform actions using an authenticated user's session.

**Implemented mitigation:** Flask-WTF CSRF protection is enabled for state-changing requests.

**Verification:** CSRF protection is part of the application configuration and should also be verified in deployment.

## 8. Session Misuse

**Threat:** An attacker reuses an exposed or improperly managed session.

**Implemented mitigation:** HTTP-only and SameSite cookie settings are configured. Secure cookies can be enabled through `COOKIE_SECURE` for HTTPS deployment.

**Remaining verification:** Production HTTPS, secure-cookie behaviour and session handling must be checked after deployment.

## 9. SQL Injection

**Threat:** Malicious input attempts to alter database queries.

**Implemented mitigation:** Database operations use SQLAlchemy rather than constructing SQL queries by concatenating untrusted input.

**Verification:** Input validation and application tests provide development-level coverage. Dedicated penetration testing remains future work.

## 10. Information Leakage

**Threat:** Error responses expose internal paths, database details or secrets.

**Mitigation:** Sensitive configuration is stored in environment variables rather than committed source files.

**Remaining verification:** Production error handling and logs must be reviewed after deployment.

## 11. Administrator Overreach

**Threat:** An administrator accesses confidential document contents without permission.

**Mitigation:** Administrative document management and metadata access are separated from owner/viewer document permissions.

**Remaining verification:** Administrative direct-download denial should be included in additional security testing.

## 12. Concurrent Permission Changes

**Threat:** A document is accessed while its permission is being revoked.

**Mitigation:** Protected operations check current database permissions.

**Remaining limitation:** Concurrent access and revocation race conditions have not been independently stress-tested.

## Accepted Risks and Future Work

- Independent external audit-log storage and checkpoints.
- Dedicated penetration testing.
- Concurrent access and permission-revocation stress tests.
- Production session and HTTPS verification.
- Additional administrative access-control tests.
- Production monitoring, backups and recovery procedures.

## Security Verification Summary

The development test suite passed 44 tests on November 7, 2026. This demonstrates the tested application behaviour; it is not a claim of complete security or production certification.