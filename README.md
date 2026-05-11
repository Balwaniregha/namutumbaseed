# Namutumba Online School Management System

This is a deploy-ready Flask + PostgreSQL School Management System.

## Main features

- Admin and teacher login
- Teacher assignment by subject and class
- Teachers see only their assigned marks entry page
- Teachers cannot view report cards, fees, admissions, users, or school setup
- S1-S4 O-Level with streams A, B, C and no combinations
- S5-S6 A-Level with Arts/Sciences and automatic combinations
- O-Level raw score + marked out of conversion to /3, then formative /20
- A-Level C1-C5, A-E grading and descriptors
- Missed assessment rule: X or - gives no grade and shows missed assessment
- Class/stream/department report card printing
- Student admissions, subject allocation, attendance, fees and partial payments
- School logo upload stored in the database

## Default logins

Admin:
- Username: admin
- Password: admin123

Sample teacher:
- Username: teacher
- Password: teacher123

Change passwords after deployment.

## Local test

```bash
pip install -r requirements.txt
python app.py
```

Open:

```text
http://127.0.0.1:5000
```

## Deploy on Render

### Option A: Blueprint deployment

1. Upload these files to a GitHub repository.
2. On Render, choose **New +** then **Blueprint**.
3. Select your GitHub repository.
4. Render will read `render.yaml` and create:
   - a Web Service
   - a PostgreSQL database
5. Wait for deployment to finish.
6. Open the Render URL and login as admin.

### Option B: Manual deployment

1. Create a PostgreSQL database on Render.
2. Create a new Web Service.
3. Connect your GitHub repository.
4. Build command:

```bash
pip install -r requirements.txt
```

5. Start command:

```bash
gunicorn app:app
```

6. Add environment variables:
   - `SECRET_KEY` = any long random text
   - `DATABASE_URL` = your Render PostgreSQL internal database URL

## Important

Do not use SQLite for real online use with many teachers. Render PostgreSQL is recommended.
