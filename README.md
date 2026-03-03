**Overview**
- **Description:** Simple generic Flask-based job runner API that exposes job creation, start/status/results endpoints and a schema endpoint used by the frontend tester.
- **Files:** See [static/tester.html](static/tester.html) for a lightweight UI used to exercise the API.

**Quick Start (Windows, recommended)**
- **Create venv and activate (PowerShell):**
```
python -m venv .venv
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process -Force
.\.venv\Scripts\Activate.ps1
```
- **Or (cmd.exe):**
```
python -m venv .venv
.\.venv\Scripts\activate.bat
```
- **Install dependencies:**
```
pip install --upgrade pip
pip install -r requirements.txt
```
- **Run app in foreground for development:**
```
python app.py
```

**Install & run as Windows service**
- This project includes `flask_service.py` which wraps the Flask app as a Windows service using pywin32. To install the service you must run the following with Administrator privileges:
```
.\.venv\Scripts\python.exe flask_service.py install
.\.venv\Scripts\python.exe flask_service.py start
```
- To stop and remove the service:
```
.\.venv\Scripts\python.exe flask_service.py stop
.\.venv\Scripts\python.exe flask_service.py remove
```
- Notes:
  - Ensure `pywin32` is installed in the environment (not included by default in all setups). If missing, install with `pip install pywin32`.
  - Service logs are appended to `service.log` in the project folder; check that file for startup errors and the resolved python path used by the service.

**Development & Testing**
- Run unit tests (if present):
```
pytest
```
- Use the built-in tester UI: open [static/tester.html](static/tester.html) in a browser (or navigate to the running app) and use `Get Schema`/`Create Job`/`Start Job` to exercise endpoints.

**How to Fork / Adapt This Project**
- **1) Provide an Action class**
  - Create a class that subclasses `ActionBase` (see [adapters.py](adapters.py)).
  - Implement `perform_action(self)` to perform your work and call `on_complete(result, error)` implicitly by returning a result (or let the framework handle it).
  - Implement `mySchema(self)` to return a JSON Schema describing a single case's action_data shape. The schema is used by `/Jobs/schema`.

- **2) Provide Results classes**
  - Subclass `ResultsBase` and implement `process_results(self)` to read `results.json` written by the completed action and return structured results.

- **3) Wire your classes into the API**
  - In `app.py` set:
    - `ActionClass = YourActionClass`
    - `ResultsClasses = [YourResultsClass, ...]`
    - Optionally set `CaseClass` if you need custom case lifecycle behavior.

- **4) (Optional) Provide a Downloadable implementation**
  - Subclass `DownloadableClass` to provide `generateDownloadable` and/or `generateDownloadableMultiple` so users can download case data in csv/json or other formats.

- **5) Test your schema & payload**
  - The tester UI fetches `/Jobs/schema` and builds a starter payload automatically — use it to validate shape and required fields before sending.

**Service-specific considerations for forks**
- If you adapt the code for non-Windows platforms, you can remove `flask_service.py` and use a native service manager (systemd, launchd, etc.) or a process supervisor (pm2, supervisor, NSSM on Windows).
- Keep application logs and job `results` in the `results/` folder; the service and the job runner rely on this structure.

**Troubleshooting**
- Missing service runtime errors: make sure `pywin32` is installed and you run install/start as Administrator.
- Port conflicts or startup errors: run `python app.py` directly to see full stack traces and fix issues before installing as a service.
- Check `service.log` after trying to start the Windows service for helpful diagnostics.

**Recommended requirements update**
- This repo imports Windows service modules in `flask_service.py` (win32serviceutil, win32service, win32event, servicemanager) which come from the `pywin32` package. If you plan to use `flask_service.py` add `pywin32` to `requirements.txt`.

**Where to start**
- For quick local testing: run the app with `python app.py`, open [static/tester.html](static/tester.html), click `Get Schema`, paste or modify the generated payload, then `Create Job`.
- For deployment as a Windows service: install the venv, install requirements, then run the `flask_service.py` install/start commands as Administrator.

---
If you want, I can: update `requirements.txt` to add `pywin32`, or add an automatic schema fetch on tester page load. Which would you like next?
