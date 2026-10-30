@echo off
setlocal
cd /d "%~dp0"

set PYTHONHOME=
set PYTHONPATH=

if "%FLASK_SECRET_KEY%"=="" set FLASK_SECRET_KEY=change-this-secret-before-production
if "%PASSWORD_STORAGE%"=="" set PASSWORD_STORAGE=legacy_plaintext
if "%SQLSERVER_ODBC_DRIVER%"=="" set SQLSERVER_ODBC_DRIVER=ODBC Driver 17 for SQL Server
if "%RAG_LOCAL_LLM%"=="" set RAG_LOCAL_LLM=1
if "%OLLAMA_MODEL%"=="" set OLLAMA_MODEL=llama3.2:3b
if "%OLLAMA_URL%"=="" set OLLAMA_URL=http://127.0.0.1:11434/api/generate

.\.venv\Scripts\python.exe -m waitress --host=0.0.0.0 --port=5000 wsgi:application
