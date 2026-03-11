import win32serviceutil
import win32service
import win32event
import servicemanager
import subprocess
import sys
import os
from datetime import datetime
from fork_config import (
    svc_name_,
    svc_display_name_,
    svc_description_
)


def _get_venv_python(venv_dir):
    return os.path.join(venv_dir, "Scripts", "python.exe")


def _run_and_log(command, cwd, log):
    log.write(f"Running: {' '.join(command)}\n")
    log.flush()
    subprocess.run(command, cwd=cwd, stdout=log, stderr=log, check=True)


def _ensure_venv_and_requirements(base_python, script_dir, log):
    venv_dir = os.path.join(script_dir, ".venv")
    venv_python = _get_venv_python(venv_dir)
    requirements_path = os.path.join(script_dir, "requirements.txt")
    marker_path = os.path.join(venv_dir, ".requirements_installed")

    if not os.path.exists(venv_python):
        log.write("Creating virtual environment...\n")
        _run_and_log([base_python, "-m", "venv", venv_dir], cwd=script_dir, log=log)

    needs_install = True
    if os.path.exists(requirements_path):
        if os.path.exists(marker_path):
            needs_install = os.path.getmtime(marker_path) < os.path.getmtime(requirements_path)
    else:
        log.write("requirements.txt not found; skipping dependency installation.\n")
        needs_install = False

    if needs_install:
        log.write("Installing dependencies from requirements.txt...\n")
        _run_and_log(
            [venv_python, "-m", "pip", "install", "--upgrade", "pip"],
            cwd=script_dir,
            log=log,
        )
        _run_and_log(
            [venv_python, "-m", "pip", "install", "-r", requirements_path],
            cwd=script_dir,
            log=log,
        )
        with open(marker_path, "w", encoding="utf-8") as marker:
            marker.write(f"installed_at={datetime.utcnow().isoformat()}Z\n")

    return venv_python

class FlaskService(win32serviceutil.ServiceFramework):
    _svc_name_ = svc_name_
    _svc_display_name_ = svc_display_name_
    _svc_description_ = svc_description_

    def __init__(self, args):
        super().__init__(args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        self.process = None

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)
        if self.process:
            self.process.terminate()

    def SvcDoRun(self):
        servicemanager.LogInfoMsg("Starting Flask service...")

        # Resolve real python.exe even when running under pythonservice.exe
        # pythonservice.exe is installed at .venv\ (venv root),
        # but python.exe lives at .venv\Scripts\python.exe
        base_python_exe = getattr(sys, "_base_executable", None) or sys.executable
        if base_python_exe.lower().endswith("pythonservice.exe"):
            _svc_dir = os.path.dirname(base_python_exe)
            _scripts_candidate = os.path.join(_svc_dir, "Scripts", "python.exe")
            _same_dir_candidate = os.path.join(_svc_dir, "python.exe")
            if os.path.exists(_scripts_candidate):
                base_python_exe = _scripts_candidate
            elif os.path.exists(_same_dir_candidate):
                base_python_exe = _same_dir_candidate

        script_dir = os.path.dirname(__file__)
        script_path = os.path.join(script_dir, "app.py")
        log_path = os.path.join(script_dir, "service.log")

        with open(log_path, "a", encoding="utf-8") as log:
            log.write("Starting Flask app...\n")
            log.write(f"Bootstrap Python: {base_python_exe}\n")
            log.write(f"Script: {script_path}\n")

            try:
                python_exe = _ensure_venv_and_requirements(base_python_exe, script_dir, log)
            except subprocess.CalledProcessError as exc:
                log.write(f"Bootstrap failed (exit code {exc.returncode}).\n")
                raise

            log.write(f"Service runtime Python: {python_exe}\n")

            self.process = subprocess.Popen(
                [python_exe, script_path],
                cwd=script_dir,
                stdout=log,
                stderr=log,
                creationflags=subprocess.CREATE_NO_WINDOW
            )

        win32event.WaitForSingleObject(self.hWaitStop, win32event.INFINITE)

if __name__ == '__main__':
    win32serviceutil.HandleCommandLine(FlaskService)
