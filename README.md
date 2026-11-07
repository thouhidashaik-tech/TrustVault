# TrustVault

TrustVault is a Flask and MySQL-based document management application.
It allows users to upload, manage and share documents with role-based
access control and document-level permissions.

## Features

- Three user roles: Admin, Owner and Viewer.
- User registration and login.
- Secure document uploads with file validation.
- Private file storage outside the public static directory.
- Document-level read and edit permissions.
- Owners can share and revoke document access.
- Search and management of documents.
- Soft deletion of documents.
- Server-side authorization checks.
- Audit records for document and permission activities.
- HMAC-SHA256 hash-linked audit events.
- Administrative user, document and activity management.
- Automated tests using pytest.

## Technology Stack

- Python
- Flask
- Flask-SQLAlchemy
- Flask-Login
- Flask-WTF
- Flask-Migrate
- MySQL
- PyMySQL
- pytest

## Requirements

- Python 3.12 or compatible version
- MySQL Server
- MySQL Workbench (optional)
- Git

## Installation on Windows

### 1. Clone the repository

```powershell
git clone YOUR_PUBLIC_GITHUB_REPOSITORY_URL
cd TrustVault