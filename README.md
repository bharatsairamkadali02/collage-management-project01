# College Management System (CMS) – Python, Flask & AWS Cloud

[![Architecture](https://img.shields.io/badge/Architecture-Two--Tier-blue.svg)](#two-tier-architecture)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB.svg?logo=python&logoColor=white)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.0.3-black.svg?logo=flask&logoColor=white)](https://flask.palletsprojects.com)
[![AWS](https://img.shields.io/badge/AWS-ap--south--1-FF9900.svg?logo=amazon-aws&logoColor=white)](https://aws.amazon.com)
[![Terraform](https://img.shields.io/badge/Terraform-1.6+-844FBA.svg?logo=terraform&logoColor=white)](https://terraform.io)
[![License](https://img.shields.io/badge/License-Proprietary-red.svg)](#)

A complete, production-grade, two-tier enterprise College Management System built with Python Flask, Bootstrap 5, and Amazon Web Services (AWS Mumbai `ap-south-1`). The application provides comprehensive Role-Based Access Control (RBAC) across three distinct user roles: **Admin**, **Faculty / Professor**, and **Student**.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Two-Tier Architecture](#2-two-tier-architecture)
3. [Technology Stack](#3-technology-stack)
4. [Folder Structure](#4-folder-structure)
5. [Database Design (Amazon RDS MySQL)](#5-database-design-amazon-rds-mysql)
6. [Role-Based Access Control (RBAC)](#6-role-based-access-control-rbac)
7. [AWS Infrastructure (Terraform)](#7-aws-infrastructure-terraform)
8. [AWS Prerequisites](#8-aws-prerequisites)
9. [Terraform Deployment Instructions](#9-terraform-deployment-instructions)
10. [Automated Application Deployment](#10-automated-application-deployment)
11. [Database Initialization & Initial Admin Setup](#11-database-initialization--initial-admin-setup)
12. [Nginx & Gunicorn Configuration](#12-nginx--gunicorn-configuration)
13. [Domain & HTTPS Configuration (TLS/SSL)](#13-domain--https-configuration-tlsssl)
14. [Operational Workflows](#14-operational-workflows)
    - [How Admin Creates Faculty Accounts](#how-admin-creates-faculty-accounts)
    - [How Admin Registers Students](#how-admin-registers-students)
    - [How Faculty Manages Attendance & Examinations](#how-faculty-manages-attendance--examinations)
    - [How Students Attend MCQ Examinations](#how-students-attend-mcq-examinations)
    - [How Results Are Evaluated & Published](#how-results-are-evaluated--published)

---

## 1. Project Overview

The College Management System is designed to manage institutional academic, operational, and student lifecycles. It consolidates student registration, faculty allocations, classroom attendance tracking, online MCQ test evaluation, assignment submissions, course study materials, tuition fee invoicing, and semester transcript publication into a unified, secure web portal.

### Core Highlights:
- **Two-Tier Deployment Model:** Nginx web server, Gunicorn application server, and Flask backend co-located on a single AWS EC2 Ubuntu 24.04 instance.
- **Relational Integrity:** Managed Amazon RDS MySQL 8.0 residing in private subnets, inaccessible from the public internet.
- **Object Storage Security:** Amazon S3 integration using Boto3 and IAM EC2 instance profiles (no static AWS secret keys in application code) for student photos, certificates, assignment submissions, and syllabi.
- **Strict Server-Side RBAC:** All protected endpoints strictly enforce authorization decorators before executing operations.
- **Automated MCQ Examination Engine:** Timed test attempts, randomized questions, client-side answer prevention, and automated grading.

---

## 2. Two-Tier Architecture

```
                          CLIENTS / WEB BROWSERS
                                    │
                                    │ HTTPS (Port 443) / HTTP (Port 80)
                                    ▼
       ┌─────────────────────────────────────────────────────────┐
       │   TIER 1: APPLICATION TIER (AWS EC2 Ubuntu 24.04 LTS)    │
       │                                                         │
       │  ┌───────────────────────────────────────────────────┐  │
       │  │               Nginx Reverse Proxy                 │  │
       │  │   • Serves static assets (/static/css, /js, /img) │  │
       │  │   • TLS/SSL Termination                           │  │
       │  │   • Proxies / dynamic routes to 127.0.0.1:8000    │  │
       │  └─────────────────────────┬─────────────────────────┘  │
       │                            │ Loopback Proxy             │
       │  ┌─────────────────────────▼─────────────────────────┐  │
       │  │           Gunicorn WSGI Application Server        │  │
       │  │   • systemd service (college-management.service)  │  │
       │  │   • 3 Sync Workers, Max Requests Recycling        │  │
       │  └─────────────────────────┬─────────────────────────┘  │
       │                            │ Python WSGI                │
       │  ┌─────────────────────────▼─────────────────────────┐  │
       │  │                Flask Application                  │  │
       │  │   • Authentication & RBAC Decorators              │  │
       │  │   • Blueprints (Admin, Faculty, Student, etc.)    │  │
       │  │   • Boto3 AWS SDK Integration                     │  │
       │  │   • SQLAlchemy ORM (PyMySQL)                      │  │
       │  └───────────────────────┬───────────────┬───────────┘  │
       └──────────────────────────┼───────────────┼──────────────┘
                                  │               │
               MySQL Port 3306    │               │  AWS IAM Role / VPC Endpoint
        (Allowed ONLY from EC2 SG)│               │  (s3:PutObject, s3:GetObject)
                                  ▼               ▼
       ┌───────────────────────────────┐ ┌───────────────────────────────┐
       │ TIER 2A: Amazon RDS MySQL 8.0 │ │   TIER 2B: Amazon S3 Bucket   │
       │ (Private Subnet Group in AZs) │ │ (Private, Server-Side Enc.)   │
       │   • 29 Relational Tables      │ │   • Student Photos & Proofs   │
       │   • Foreign Keys, Transcripts │ │   • Assignments & Solutions   │
       │   • Audit Trail, Auth Hashes  │ │   • Lecture Notes & Syllabi   │
       └───────────────────────────────┘ └───────────────────────────────┘
```

---

## 3. Technology Stack

### Frontend Tier:
- **HTML5 & CSS3:** Semantic markup, responsive flexbox/grid styling.
- **Bootstrap 5.3 & Bootstrap Icons:** Modern dashboard cards, modals, form states, and interactive tabs.
- **Vanilla JavaScript (ES6+):** CSRF fetch API helper, live timer, dynamic marks calculation, and client-side validation.

### Backend Application Tier:
- **Python 3.11+ & Flask 3.0.3:** Modular application factory architecture with 10 feature Blueprints.
- **Flask-Login 0.6.3:** Secure session-based authentication with 8-hour cookie lifetime.
- **Flask-SQLAlchemy 3.1.1 & PyMySQL 1.1.1:** ORM data mapping with connection pool recycling.
- **Flask-Migrate 4.0.7:** Alembic database version control.
- **Flask-WTF 1.2.1:** Synchronizer token pattern CSRF defense.
- **Werkzeug 3.0.3:** PBKDF2 password hashing with salt.
- **Boto3 1.34.144:** AWS SDK for presigned URLs and S3 uploads.
- **Gunicorn 22.0.0:** Multi-worker WSGI HTTP production server.
- **Nginx:** High-performance reverse proxy and static cache.

### Database & Storage Tier:
- **Amazon RDS for MySQL 8.0:** Multi-AZ private subnet deployment with automated snapshots.
- **Amazon S3:** Private bucket with AES-256 server-side encryption and Block Public Access enabled.

---

## 4. Folder Structure

```
college-management-system/
├── .github/
│   └── workflows/
│       └── deploy.yml              # Optional CI/CD deployment workflow
├── backend/
│   ├── app.py                      # Flask Application Factory (create_app)
│   ├── config.py                   # Development & Production Config classes
│   ├── database.py                 # DB Bootstrap, Seeding & Health Check API
│   ├── extensions.py               # db, migrate, login_manager, csrf instances
│   ├── requirements.txt            # Production Python package manifest
│   ├── .env.example                # Sample environment variables
│   ├── models/
│   │   ├── __init__.py             # Model exports and backward-compatible aliases
│   │   ├── user.py                 # User, Role, Permission, RolePermission
│   │   ├── student.py              # Student personal & academic profile
│   │   ├── faculty.py              # Faculty profile and HOD designations
│   │   ├── department.py           # Academic Departments
│   │   ├── subject.py              # AcademicYear, Semester, Subject
│   │   ├── class_section.py        # ClassSection, FacultyAssignment, Enrollment
│   │   ├── attendance.py           # AttendanceSession & AttendanceRecord
│   │   ├── examination.py          # Exam, Question, Option, Attempt, Answer
│   │   ├── results.py              # Semester Result and Grade calculations
│   │   ├── fees.py                 # FeeRecord & FeePayment
│   │   ├── assignments.py          # Assignment, Submission, StudyMaterial
│   │   ├── notifications.py        # System Notifications
│   │   ├── audit.py                # AuditLog model with log_action helper
│   │   └── documents.py            # StudentDocument (S3 metadata)
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── auth.py                 # Login, Logout, Password Recovery
│   │   ├── admin.py                # Admin Dashboard & Entity Management
│   │   ├── faculty.py              # Faculty Dashboard, Marks, Exams
│   │   ├── students.py             # Student Dashboard, Exam Runner, Fees
│   │   ├── attendance.py           # Attendance REST endpoints
│   │   ├── examinations.py         # Exam lifecycle REST endpoints
│   │   ├── results.py              # Results evaluation & publish REST API
│   │   ├── fees.py                 # Fee management REST API
│   │   ├── assignments.py          # Assignments REST API
│   │   └── notifications.py        # Notifications REST API
│   ├── security/
│   │   ├── __init__.py
│   │   ├── permissions.py          # 40+ granular RBAC permission strings
│   │   └── decorators.py           # @admin_required, @faculty_required, etc.
│   ├── services/
│   │   ├── __init__.py
│   │   ├── s3_service.py           # Boto3 S3 upload & presigned URL service
│   │   ├── attendance_service.py   # Attendance percentage calculator
│   │   ├── exam_service.py         # MCQ eligibility, timer & auto-grader
│   │   └── result_service.py       # Grade conversion & SGPA compilation
│   ├── static/
│   │   ├── css/
│   │   │   └── main.css            # EduManage Pro theme stylesheet
│   │   └── js/
│   │       └── main.js             # Common JavaScript API fetch & toast helpers
│   └── templates/
│       ├── base.html               # Master layout with topbar & responsive sidebar
│       ├── login.html              # Standalone login template
│       ├── forgot-password.html    # Forgot password template
│       ├── reset-password.html     # Reset password template
│       ├── admin/                  # 18 Admin module templates
│       ├── faculty/                # 12 Faculty module templates
│       ├── student/                # 10 Student module templates
│       └── errors/                 # 400, 403, 404, 500 error templates
├── config/
│   ├── college-management.service  # systemd service unit file for Gunicorn
│   └── nginx.conf                  # Nginx reverse proxy configuration
├── database/
│   └── schema.sql                  # Complete MySQL DDL schema and seed data
├── scripts/
│   └── deploy.sh                   # Automated SSH/SCP remote deployment script
└── terraform/
    ├── main.tf                     # AWS VPC, Subnets, EC2, RDS, S3, IAM
    ├── variables.tf                # Input variables with descriptions
    ├── outputs.tf                  # Infrastructure outputs (IP, RDS endpoint)
    ├── terraform.tfvars.example    # Variable definitions template
    └── user_data.sh                # EC2 cloud-init provisioning script
```

---

## 5. Database Design (Amazon RDS MySQL)

The system database is named `college_management` and contains **29 interconnected tables**:

| Category | Tables | Description |
| :--- | :--- | :--- |
| **Authentication & RBAC** | `roles`, `permissions`, `role_permissions`, `users` | PBKDF2 hashes, session status, user roles, permission mappings |
| **Academic Structure** | `departments`, `academic_years`, `semesters`, `subjects`, `class_sections` | College curriculum, credit rules, semester term dates, classrooms |
| **Personnel Profiles** | `faculty`, `students`, `faculty_assignments`, `student_enrollments` | Profiles, HOD flags, subject allocations, student enrollments |
| **Attendance Management**| `attendance_sessions`, `attendance_records` | Daily sessions, Present/Absent/Late/Leave tracking, remarks |
| **Online MCQ Examination**| `exams`, `questions`, `question_options`, `exam_attempts`, `attempt_answers` | Timed exams, shuffled options, auto-scoring, attempt tracking |
| **Grading & Results** | `results` | Internal (40), External (60), Total, Percentage, Letter Grade, Pass/Fail |
| **Fee Management** | `fee_records`, `fee_payments` | Tuition dues, payment modes, receipts, waivers, balances |
| **Coursework & Documents**| `assignments`, `assignment_submissions`, `study_materials`, `student_documents` | S3 keys, submission status, grades, verification status |
| **Audit & Communication** | `notifications`, `audit_logs` | Role-targeted announcements, immutable action logs |

---

## 6. Role-Based Access Control (RBAC)

The system enforces complete Role-Based Access Control at the application router level using Python decorators:

```python
# Security decorator hierarchy:
@login_required              # Enforces valid session cookie
@admin_required              # Restricts route strictly to Admin role
@faculty_required            # Restricts route strictly to Faculty role
@student_required            # Restricts route strictly to Student role
@permission_required(NAME)   # Validates granular permission against role_permissions
```

### Permission Matrix Summary:
- **Admin:** Superuser with unrestricted access across all modules. Can create faculty and students, reset passwords, create fee records, manage departments, publish semester results, and inspect audit logs.
- **Faculty:** Scoped academic access. Can mark attendance for assigned class sections, create MCQ examinations, enter internal/external marks, upload study materials to S3, and send class notices. Cannot register users or alter fees.
- **Student:** Strict read-only access to own profile, attendance percentage, fee status, and published results. Can attend MCQ exams and submit assignment files to S3. Cannot access answers or peer records.

---

## 7. AWS Infrastructure (Terraform)

All AWS infrastructure is codified in HCL under `terraform/` targeting the **ap-south-1 (Mumbai)** region:

- **Virtual Private Cloud (VPC):** `10.0.0.0/16` with DNS hostnames enabled.
- **Public Subnet:** `10.0.1.0/24` (AZ `ap-south-1a`) hosting the EC2 instance and Internet Gateway (IGW).
- **Private Subnets:** `10.0.2.0/24` (`ap-south-1a`) and `10.0.3.0/24` (`ap-south-1b`) hosting the Amazon RDS MySQL DB subnet group.
- **Security Groups:**
  - `ec2_sg`: Allows Inbound Port 80 (HTTP), Port 443 (HTTPS), Port 22 (SSH from authorized CIDR), and Port 8000 internally.
  - `rds_sg`: Allows Inbound Port 3306 **only** from `ec2_sg.id` (strictly preventing public database access).
- **Amazon RDS MySQL 8.0:** `db.t3.micro` / `db.t3.small` instance with storage encryption, automated backups, and `publicly_accessible = false`.
- **Amazon S3 Bucket:** Private bucket with AES-256 encryption, public access block enabled, and CORS rules.
- **AWS IAM Role & Instance Profile:** Attached to EC2 to grant `s3:PutObject`, `s3:GetObject`, and `s3:DeleteObject` permissions without credentials in Python source code.
- **Elastic IP (EIP):** Static public IPv4 allocated to the EC2 instance.

---

## 8. AWS Prerequisites

Before deploying, ensure you have:
1. An active **AWS Account** with administrative permissions.
2. **AWS CLI v2** installed and configured:
   ```bash
   aws configure
   # Default region name: ap-south-1
   ```
3. An **EC2 Key Pair** created in `ap-south-1`:
   ```bash
   aws ec2 create-key-pair --key-name college-key --query 'KeyMaterial' --output text > ~/.ssh/college-key.pem
   chmod 400 ~/.ssh/college-key.pem
   ```
4. **Terraform v1.6+** installed on your administrative machine.

---

## 9. Terraform Deployment Instructions

### Step 1: Configure Terraform Variables
```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
```
Edit `terraform.tfvars`:
```hcl
aws_region       = "ap-south-1"
project_name     = "college-management"
environment      = "production"
key_pair_name    = "college-key"
allowed_ssh_cidr = "YOUR_OFFICE_OR_HOME_IP/32"
db_username      = "college_admin"
db_password      = "YourStrongDBPassword123!"
s3_bucket_name   = "college-cms-storage-unique-id"  # Must be globally unique
```

### Step 2: Provision Cloud Resources
```bash
terraform init
terraform plan
terraform apply -auto-approve
```

### Step 3: Note Down Infrastructure Outputs
Terraform will display the outputs upon completion:
```
ec2_public_ip       = "13.233.X.X"
rds_endpoint        = "college-management-rds.c123456789.ap-south-1.rds.amazonaws.com:3306"
s3_bucket_name      = "college-cms-storage-unique-id"
```

---

## 10. Automated Application Deployment

You do **not** need a local Python development environment. Use the provided automated deployment script:

```bash
export EC2_HOST="13.233.X.X"
export EC2_KEY_PATH="~/.ssh/college-key.pem"
export DB_HOST="college-management-rds.c123456789.ap-south-1.rds.amazonaws.com"
export DB_PASSWORD="YourStrongDBPassword123!"
export S3_BUCKET="college-cms-storage-unique-id"
export SECRET_KEY="$(openssl rand -hex 32)"
export ADMIN_EMAIL="admin@college.edu"
export ADMIN_PASSWORD="Admin@123Change!"

bash scripts/deploy.sh
```

### What `deploy.sh` Automatically Performs:
1. Connects to the EC2 instance via SSH.
2. Installs system packages: `python3-pip`, `python3-venv`, `nginx`, `git`.
3. Creates a dedicated Linux application user (`appuser`).
4. Clones application source code to `/opt/college-app`.
5. Builds a Python virtual environment and installs `requirements.txt`.
6. Configures `/opt/college-app/.env` with secure credentials.
7. Executes `database.py` to seed roles, permissions, and the initial Admin account.
8. Configures the systemd service `/etc/systemd/system/college-management.service`.
9. Configures `/etc/nginx/sites-available/college-management` and enables it.
10. Restarts Gunicorn and reloads Nginx.

---

## 11. Database Initialization & Initial Admin Setup

If deploying manually or verifying the database, execute inside the EC2 virtual environment:

```bash
cd /opt/college-app/backend
source /opt/college-app/venv/bin/activate
python database.py
```

### Initial Admin Credentials:
The Admin account is automatically seeded using the environment variables:
- **Email:** Value of `INITIAL_ADMIN_EMAIL` (default: `admin@college.edu`)
- **Password:** Value of `INITIAL_ADMIN_PASSWORD` (default: `Admin@123Change`)
- **Login URL:** `http://<EC2_PUBLIC_IP>/auth/login`

> **Security Note:** Always change the initial admin password immediately upon your first login.

---

## 12. Nginx & Gunicorn Configuration

### Gunicorn Systemd Service:
Configured at `/etc/systemd/system/college-management.service`:
```ini
[Unit]
Description=College Management System - Gunicorn
After=network.target

[Service]
User=appuser
Group=appuser
WorkingDirectory=/opt/college-app/backend
Environment=PATH=/opt/college-app/venv/bin
EnvironmentFile=/opt/college-app/.env
ExecStart=/opt/college-app/venv/bin/gunicorn --workers 3 --bind 127.0.0.1:8000 --timeout 120 app:create_app()
Restart=always

[Install]
WantedBy=multi-user.target
```

### Manage the Service:
```bash
sudo systemctl status college-management
sudo systemctl restart college-management
sudo journalctl -u college-management -f
```

---

## 13. Domain & HTTPS Configuration (TLS/SSL)

To attach a custom domain (e.g. `college.yourdomain.com`) and enable free SSL certificates:

1. In your DNS provider (e.g. Route 53, Cloudflare, GoDaddy), point an **A record** to the `EC2_PUBLIC_IP`.
2. SSH into your EC2 instance:
   ```bash
   sudo apt-get install -y certbot python3-certbot-nginx
   sudo certbot --nginx -d college.yourdomain.com
   ```
3. Certbot will update the Nginx configuration, provision a Let's Encrypt TLS certificate, and set up automatic certificate renewal via cron.

---

## 14. Operational Workflows

### How Admin Creates Faculty Accounts
1. Log in as **Admin** at `/auth/login`.
2. Navigate to **Faculty** in the sidebar (`/admin/faculty`) and click **Add Faculty**.
3. Fill in account credentials (First Name, Last Name, Email, Username, Temporary Password).
4. Select the **Department**, **Designation**, **Specialization**, and **Employment Type**.
5. Optionally upload a profile photo directly to Amazon S3.
6. Click **Register Faculty**. The professor can now sign in using their assigned credentials.

### How Admin Registers Students
1. Log in as **Admin** and navigate to **Students** (`/admin/students`).
2. Click **Register New Student** (`/admin/students/add`).
3. Complete the multi-tab form:
   - **Personal Info:** Name, Institutional Email, Date of Birth, Gender, Phone.
   - **Academic Info:** Roll Number, Registration Number, Department, Semester, Class Section.
   - **Address & Guardian Details:** Full contact address and emergency guardian details.
4. Click **Register Student**. The student login account and enrollment records are generated.

### How Faculty Manages Attendance & Examinations
1. Log in as **Faculty** at `/auth/login`.
2. **Mark Daily Attendance:**
   - Go to **Attendance** (`/faculty/attendance`).
   - Select Class Section, Subject, Date, and Session Type (Lecture / Lab).
   - Click **Load Students**, toggle radio buttons (Present, Absent, Late, Leave), or click **Mark All Present**, and click **Save Attendance**.
3. **Create Online MCQ Exam:**
   - Go to **Examinations** (`/faculty/examinations`) and click **Create Exam**.
   - Set Title, Subject, Duration, Passing Marks, Start Time, and End Time window.
   - Add MCQ questions with 4 options, select the correct radio button, and set question marks.
   - Click **Publish**. The exam is now available to students enrolled in that class section.

### How Students Attend MCQ Examinations
1. Log in as **Student** at `/auth/login`.
2. Navigate to **Examinations** (`/student/examinations`).
3. If an exam is within its active schedule window, click **Start Exam**.
4. The exam runner interface displays:
   - Live Countdown Timer.
   - Question navigation palette.
   - Radio buttons for selecting responses.
5. Answers are saved to the backend as they are selected.
6. When the timer reaches 00:00 or when the student clicks **Submit Exam**, answers are auto-evaluated on the server.

### How Results Are Evaluated & Published
1. **Faculty Enters Scores:** Navigate to **Marks Entry** (`/faculty/marks`), load the class section, and input Internal (out of 40) and External (out of 60) marks. The system automatically computes total scores, percentages, and letter grades (`O`, `A+`, `A`, `B+`, `B`, `C`, `D`, `F`).
2. **Admin Publishes Results:** The Admin verifies scores at `/admin/results` and clicks **Publish Semester Results**.
3. **Student Viewing:** Once published, students can instantly view their semester transcript and grade standing at `/student/results`.

---

## 15. License

Proprietary College Management System designed for institutional deployment on AWS Cloud. All rights reserved.
