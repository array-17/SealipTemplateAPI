import win32serviceutil
import win32service
import win32event
import servicemanager
import subprocess
import sys
import os

class FlaskService(win32serviceutil.ServiceFramework):
    _svc_name_ = "AddAppService"
    _svc_display_name_ = "AddApp Flask App Service"
    _svc_description_ = "Runs the AddApp Flask app as a Windows service."

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
        python_exe = getattr(sys, "_base_executable", None) or sys.executable
        if python_exe.lower().endswith("pythonservice.exe"):
            python_exe = os.path.join(os.path.dirname(python_exe), "python.exe")

        script_dir = os.path.dirname(__file__)
        script_path = os.path.join(script_dir, "app.py")
        log_path = os.path.join(script_dir, "service.log")

        with open(log_path, "a", encoding="utf-8") as log:
            log.write("Starting Flask app...\n")
            log.write(f"Python: {python_exe}\n")
            log.write(f"Script: {script_path}\n")

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
