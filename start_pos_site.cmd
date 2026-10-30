@echo off
cd /d D:\SoftwareGIT\PythonAuth
set PYTHONHOME=
set PYTHONPATH=
set PASSWORD_STORAGE=legacy_plaintext
set SQLSERVER_ODBC_DRIVER=ODBC Driver 17 for SQL Server
.\.venv_server3124\Scripts\python.exe -m waitress --host=127.0.0.1 --port=5000 wsgi:application