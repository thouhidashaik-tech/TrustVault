# TrustVault — AI Usage Journal

**Project:** TrustVault  
**Developer:** Thouhida Shaik

AI tools were used as development assistants for understanding requirements, learning Flask concepts, debugging, reviewing code and preparing tests. I reviewed the suggestions, applied changes to my project and verified the behaviour through testing.

## 1. November 1, 2026 — Project Planning

**Prompt:** Understand the TrustVault challenge requirements and suggest a suitable technology stack and development plan.

**AI Output:** Suggested Flask, MySQL and a modular application structure.

**Issue Identified:** The initial plan needed more attention to document-level authorization, private file storage and audit integrity.

**My Action:** Prioritised server-side access checks, secure document storage and audit logging before optional features.

**Commit:** Planning stage; no implementation commit.

## 2. November 2, 2026 — Project Setup

**Prompt:** Guide me through creating a Flask application with Git, a Python virtual environment and MySQL.

**AI Output:** Provided setup commands, configuration guidance and a suggested project structure.

**Issues Encountered:** Git was initially not recognised in VS Code, Python and pip commands had PATH issues, and PowerShell blocked virtual-environment activation.

**My Action:** Troubleshot the environment, used the virtual-environment Python executable directly and verified the Flask-to-MySQL connection.

**Commit:** `87c2c5a` — Initial TrustVault project setup.

## 3. November 2–3, 2026 — Audit Chain Initialization

**Prompt:** Help implement a cryptographically linked audit log and a command to initialise its starting event.

**AI Output:** Suggested HMAC-SHA256 signatures and previous-event hash linking.

**Issue Identified:** A hash chain alone does not protect against an attacker who can rewrite the entire database and access the signing secret.

**My Action:** Documented this limitation in the threat model and kept the HMAC secret in environment configuration.

**Commit:** `15b2a09` — Add audit chain initialization command.

## 4. November 5–6, 2026 — Authorization and Audit Tests

**Prompt:** Review document and administrator routes and help test role-based access control.

**AI Output:** Suggested additional tests for administrator actions and authorization boundaries.

**AI Mistake Identified:** An initial proposed last-active-administrator test created an inactive second administrator and then tested self-deactivation. That did not actually exercise the intended last-active-administrator condition.

**My Correction:** Replaced that misleading test with a test that creates another active administrator, deactivates that account and verifies the resulting database state and audit event. I did not treat the original test as proof of the last-active-admin protection.

**Commit:** `4ba95c5` — Improve document audit logging and add admin tests.

## 5. November 7, 2026 — Audit Chain Integrity Improvements

**Prompt:** Review audit-chain verification and identify ways to detect chain resets and deletion of audit records.

**AI Output:** Suggested using the earliest signed genesis event as the verification baseline, rejecting a second genesis event through the application audit function, and testing chain continuity.

**My Action:** Updated `app/audit.py` and added tests for:
- Rejecting a second genesis event.
- Detecting deletion of a middle audit event.
- Detecting modified audit details.
- Detecting missing event signatures.
- Verifying a valid audit chain.

**Verification:** The complete automated test suite passed 44 tests on November 7, 2026.

**Commit:** `a1b5328` — Strengthen audit chain integrity checks.

## AI Tools Used

- ChatGPT — requirements analysis, learning Flask concepts, code suggestions, debugging, test design, documentation and security review.
- Visual Studio Code — code editing and project development.
- Git and GitHub — source control and commit history.

## What I Learned About Using AI

AI-generated code is not automatically correct. I learned to review suggestions, question whether a test actually proves the intended security condition, run automated tests and document limitations instead of claiming that a feature is completely secure.

I used AI as an assistant, but I remained responsible for applying changes and checking the application behaviour.