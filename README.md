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


## Live Demo

- **Live Application:** https://trustvault-95p2.onrender.com
- **Demo Video:** https://drive.google.com/file/d/1afWSTyh_v9HLd1yauAK-VFAEpLNniByB/view?usp=drivesdk


## How TrustVault Works

TrustVault is a secure document-sharing platform that helps organizations share confidential documents with controlled access and maintain an audit trail of user activities.

### 1. User Roles

The application supports three roles:

- **Admin:** Manages users and monitors application activity through the Admin Dashboard.
- **Owner:** Uploads documents, manages uploaded documents, shares documents with authorized users, and controls access.
- **Viewer:** Accesses documents shared with them and can view or download permitted documents.

### 2. Application Workflow

1. The Admin logs in to the application.
2. The Admin creates Owner and Viewer accounts through User Management.
3. The Owner logs in and accesses the Owner Dashboard.
4. The Owner uploads confidential documents.
5. The Owner shares documents with specific authorized users.
6. Viewers log in and access only the documents shared with them.
7. Owners can manage sharing permissions and revoke access when required.
8. The application records document-related activities in its audit trail.
9. Administrators can monitor user activity through the Admin Dashboard.

### 3. Security Features

- Role-based access control.
- Secure authentication.
- Document-level access permissions.
- Access revocation.
- Document soft deletion.
- Audit logging of document activities.
- Secure document upload and download handling.

### 4. Getting Started

1. Open the deployed application: https://trustvault-95p2.onrender.com
2. Log in using the authorized Admin account.
3. Create Owner and Viewer accounts through User Management.
4. Log in with the newly created accounts to explore their respective dashboards and features.

**Note:** TrustVault does not require public self-registration. User accounts are managed by the Admin. Demo credentials, if provided, should be shared separately and never committed to the public repository.

