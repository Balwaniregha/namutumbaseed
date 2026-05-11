NAMUTUMBA SMS - EASY RENDER DEPLOYMENT

IMPORTANT:
Upload the files in this folder directly to GitHub.
Do not upload the parent folder and do not upload the ZIP file.

GitHub repository should show these files on the first page:
- app.py
- requirements.txt
- render.yaml
- Procfile
- runtime.txt
- templates/
- static/

Render Web Service settings:
Language/Runtime: Python
Root Directory: leave blank
Build Command: pip install -r requirements.txt
Start Command: gunicorn app:app

If Render asks for Environment Variables:
SECRET_KEY = any long secret text
DATABASE_URL = the Internal Database URL from your Render PostgreSQL database

Default login:
Admin username: admin
Admin password: admin123
Teacher username: teacher
Teacher password: teacher123
