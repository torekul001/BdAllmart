# All Servicer Python Deployment

## Server Requirements

- Windows Server
- Python 3.11 or newer
- Microsoft ODBC Driver 17 or 18 for SQL Server
- Network access from the server to SQL Server `103.159.73.66`

## Copy Files

Copy this folder to the server:

```text
PythonAuth
```

Keep these folders with it:

```text
static
templates
```

## Install

Open PowerShell in the `PythonAuth` folder:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Environment

Set a production secret key:

```powershell
setx FLASK_SECRET_KEY "replace-with-a-long-random-secret"
setx PASSWORD_STORAGE "legacy_plaintext"
setx SQLSERVER_ODBC_DRIVER "ODBC Driver 17 for SQL Server"
```

Optional: if `web.config` is not available on the server, set the DB connection string:

```powershell
setx ALLSERVICER_DB_CONN_STR "Data Source=103.159.73.66;Initial Catalog=BdOnlinePlatform; User Id=sa; Password=Abc@#123ht;"
```

Close and reopen PowerShell after `setx`.

## Run

```powershell
.\run_production.cmd
```

Open:

```text
http://server-ip:5000/login
```

## IIS / Domain

Recommended production setup:

1. Run this Python app with `run_production.cmd` on `127.0.0.1:5000`.
2. In IIS, use URL Rewrite + ARR reverse proxy.
3. Point the domain to `http://127.0.0.1:5000`.
4. Bind SSL certificate in IIS.

## Keep App Running

Use one of these:

- NSSM Windows service running `run_production.cmd`
- Windows Task Scheduler at startup
- IIS reverse proxy plus a Windows service

## Important

Do not run `python app.py` in production because it starts Flask debug server.
