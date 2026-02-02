@echo off
echo Starting Celery Worker (Windows Mode)...
set PYTHONPATH=%CD%
"C:\Users\ankit\AppData\Local\Programs\Python\Python312\python.exe" -m celery -A app.core.celery_app worker --loglevel=info --pool=solo
pause
