# server_manager/web_server.py
import http.server
import socketserver
import os
import socket
import threading
import subprocess
import time
import sys
from PyQt5.QtCore import QObject, pyqtSignal

from .config import DEFAULT_PORT, SERVER_TYPES

class WebServer(QObject):
    log_signal = pyqtSignal(str) # لطباعة الرسائل في واجهة المستخدم
    server_started = pyqtSignal(bool) # لإعلام الواجهة بأن الخادم بدأ

    def __init__(self, port=DEFAULT_PORT, log_signal=None):
        super().__init__()
        self.port = port
        self.httpd = None 
        self.server_thread = None
        self.server_type = None
        self.project_path = None
        self.django_process = None # لعمليات Static/Django/Flask
        self.php_process = None # عملية خادم PHP
        if log_signal:
            self.log_signal = log_signal

    def is_running(self):
        # التحقق من حالة الخوادم
        if self.django_process and self.django_process.poll() is None:
            return True
        if self.php_process and self.php_process.poll() is None:
            return True
        return False
    
    def _get_project_name(self, project_path):
        return os.path.basename(project_path)

    def _is_port_available(self, port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("0.0.0.0", port))
                return True
            except socket.error:
                return False

    def get_local_and_ip_addresses(self):
        addresses = []
        try:
            local_ip = "127.0.0.1"
            hostname = socket.gethostname()
            ip_address = socket.gethostbyname(hostname)

            addresses.append(f"http://{local_ip}:{self.port}")
            if ip_address != local_ip:
                addresses.append(f"http://{ip_address}:{self.port}")
        except socket.error as e:
            self.log_signal.emit(f"Error getting network addresses: {e}")
        return addresses

    def start(self, project_path, port, server_type_id):
        self.stop() 
        
        if not self._is_port_available(port):
            self.log_signal.emit(f"Error: Port {port} is already in use. Please choose another port.")
            self.server_started.emit(False)
            return False

        self.port = port
        self.server_type = server_type_id
        self.project_path = project_path

        self.log_signal.emit(f"Attempting to start server type: {SERVER_TYPES.get(server_type_id, server_type_id)} on port {port}")
        
        if server_type_id == "http.server":
            self.log_signal.emit("Starting Static File Server (Python http.server)...")
            try:
                command = [
                    sys.executable,
                    '-m', 
                    'http.server',
                    str(port)
                ]
                
                self.django_process = subprocess.Popen( 
                    command,
                    cwd=project_path,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                
                # التحقق السريع
                time.sleep(1)
                if self.django_process.poll() is not None:
                    self.log_signal.emit(f"Static server process terminated immediately. Check Python installation.")
                    self.server_started.emit(False)
                    self.django_process = None
                    return False

                threading.Thread(target=self._monitor_django_logs, daemon=True).start() 
                self.log_signal.emit(f"Static File Server running at http://0.0.0.0:{port}")
                self.server_started.emit(True)
                return True
            except Exception as e:
                self.log_signal.emit(f"Failed to start http.server via subprocess: {e}")
                self.django_process = None
                self.server_started.emit(False)
                return False

        elif server_type_id == "flask":
            self.log_signal.emit("Starting Flask Application (assuming 'app.py' or equivalent)...")
            try:
                flask_file = os.path.join(project_path, 'app.py') 
                if not os.path.exists(flask_file):
                    self.log_signal.emit(f"Error: Could not find main Flask file (e.g., app.py) in {project_path}")
                    self.server_started.emit(False)
                    return False
                    
                command = [
                    sys.executable,
                    '-m', 
                    'flask',
                    'run',
                    '--host', '0.0.0.0', 
                    '--port', str(port)
                ]
                
                env = os.environ.copy()
                env['FLASK_APP'] = os.path.basename(flask_file) 

                self.django_process = subprocess.Popen(
                    command,
                    cwd=project_path,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    env=env 
                )
                
                time.sleep(1)
                if self.django_process.poll() is not None:
                    self.log_signal.emit(f"Flask process terminated immediately. Check dependencies (pip install flask) or code errors.")
                    self.server_started.emit(False)
                    self.django_process = None
                    return False

                threading.Thread(target=self._monitor_django_logs, daemon=True).start()
                self.log_signal.emit(f"Flask Server running at http://0.0.0.0:{port}")
                self.server_started.emit(True)
                return True
            except Exception as e:
                self.log_signal.emit(f"Failed to start Flask server: {e}")
                self.django_process = None
                self.server_started.emit(False)
                return False

        elif server_type_id == "django":
            self.log_signal.emit(f"Starting Django Application in '{self._get_project_name(project_path)}'...")
            try:
                command = [
                    sys.executable,
                    'manage.py', 
                    'runserver', 
                    f'0.0.0.0:{port}'
                ]
                
                self.django_process = subprocess.Popen(
                    command,
                    cwd=project_path,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                
                time.sleep(1)
                if self.django_process.poll() is not None:
                    self.log_signal.emit(f"Django process terminated immediately. Check dependencies (pip install django) or code errors.")
                    self.server_started.emit(False)
                    self.django_process = None
                    return False

                threading.Thread(target=self._monitor_django_logs, daemon=True).start()
                self.log_signal.emit(f"Django Server running at http://0.0.0.0:{port}")
                self.server_started.emit(True)
                return True
            except FileNotFoundError:
                self.log_signal.emit("Error: Python interpreter or 'manage.py' not found. Ensure you are in the correct Django project directory.")
                self.django_process = None
                self.server_started.emit(False)
                return False
            except Exception as e:
                self.log_signal.emit(f"Failed to start Django server: {e}")
                self.django_process = None
                self.server_started.emit(False)
                return False

        elif server_type_id == "php_server": 
            self.log_signal.emit("Starting PHP Built-in Server...")
            success = self._run_php_server(port, project_path)
            self.server_started.emit(success)
            return success

        else:
            self.log_signal.emit(f"Error: Unknown server type ID: {server_type_id}")
            self.server_started.emit(False)
            return False

    def _run_php_server(self, port, doc_root):
        """Runs the PHP built-in server in a subprocess and monitors its output."""
        try:
            host = "0.0.0.0"
            command = [
                "php",
                "-S",
                f"{host}:{port}",
                "-t",
                doc_root
            ]

            self.php_process = subprocess.Popen(
                command,
                cwd=doc_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1, 
                universal_newlines=True,
                shell=True # 🚨 الإصلاح الحاسم 🚨
            )
            
            time.sleep(2)
            if self.php_process.poll() is not None:
                self.log_signal.emit(f"PHP process terminated immediately. Check PHP installation (php -v) or port conflict.")
                self.php_process = None
                return False

            self.log_signal.emit(f"PHP Server running at http://{host}:{port}")
            self.log_signal.emit(f"Document Root: {doc_root}")
            
            self.server_thread = threading.Thread(target=self._monitor_php_logs, daemon=True)
            self.server_thread.start()

        except FileNotFoundError:
            self.log_signal.emit("Error: 'php' command not found. Please ensure PHP CLI is installed and in your system's PATH.")
            self.php_process = None
            return False
        except Exception as e:
            self.log_signal.emit(f"Failed to start PHP server: {e}")
            self.php_process = None
            return False

        return True

    def _monitor_php_logs(self):
        """Monitors stdout and stderr for the PHP server process."""
        # FIX: استخدام مرجع محلي لتجنب سباق الشروط (Race Condition)
        process = self.php_process 
        if process is None:
            return

        try:
            if process.stdout:
                for line in iter(process.stdout.readline, ''):
                    if line:
                        self.log_signal.emit(f"[PHP]: {line.strip()}")

            if process.stderr:
                for line in iter(process.stderr.readline, ''):
                    if line:
                        self.log_signal.emit(f"[PHP-LOG]: {line.strip()}")

        except Exception as e:
            self.log_signal.emit(f"[PHP Monitor Error]: {e}")
        finally:
            if process:
                process.wait()
                if process.stdout:
                    process.stdout.close()
                if process.stderr:
                    process.stderr.close()
            
            self.log_signal.emit("PHP process terminated.")
            
            # FIX: شرط إضافي قبل تعيين المتغير العام لـ None
            if self.php_process is process:
                self.php_process = None
            
    def _monitor_django_logs(self):
        """Monitors stdout and stderr for Django/Flask/Static process."""
        # FIX: استخدام مرجع محلي لتجنب سباق الشروط (Race Condition)
        process = self.django_process
        if process is None:
            return
            
        try:
            if process.stdout:
                for line in process.stdout:
                    self.log_signal.emit(f"[SERVER]: {line.decode().strip()}")
            if process.stderr:
                for line in process.stderr:
                    self.log_signal.emit(f"[SERVER-ERR]: {line.decode().strip()}")
        except Exception as e:
            self.log_signal.emit(f"[Monitor Error]: {e}")
        finally:
            if process:
                process.wait()
                # التأكد من وجود stdout/stderr قبل الإغلاق
                if process.stdout: 
                    process.stdout.close()
                if process.stderr:
                    process.stderr.close()
                self.log_signal.emit("Python Server Process terminated.")
                
                # FIX: شرط إضافي قبل تعيين المتغير العام لـ None
                if self.django_process is process: 
                    self.django_process = None

    def stop(self):
        """Stops the currently running web server."""
        self.server_started.emit(False) 

        # 1. إيقاف عملية Static/Django/Flask
        if self.django_process:
            self.log_signal.emit("Stopping Python Server Process...")
            try:
                self.django_process.terminate()
                self.django_process.wait(timeout=5)
            except:
                self.django_process.kill()
            self.django_process = None # يتم تعيينه لـ None لتجنب رؤية عملية قديمة في start()
            self.log_signal.emit("Python Server Process stopped.")
            
        # 2. إيقاف عملية PHP
        if self.php_process:
            self.log_signal.emit("Stopping PHP Server...")
            try:
                self.php_process.terminate()
                self.php_process.wait(timeout=5)
            except:
                self.php_process.kill()
            self.php_process = None
            self.log_signal.emit("PHP Server stopped.")
            
        self.log_signal.emit("Server stopped successfully.")

# Workers for QThreads (دوال مساعدة لـ PyQt5)
class ServerStarter(QObject):
    finished = pyqtSignal(bool)
    error = pyqtSignal(str)

    def __init__(self, server_instance, project_path, port, server_type_id):
        super().__init__()
        self.server_instance = server_instance
        self.project_path = project_path
        self.port = port
        self.server_type_id = server_type_id

    def start_server(self):
        try:
            success = self.server_instance.start(self.project_path, self.port, self.server_type_id)
            self.finished.emit(success)
        except Exception as e:
            self.error.emit(f"Failed to start server: {e}")
            self.finished.emit(False)

class ServerStopper(QObject):
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, server_instance):
        super().__init__()
        self.server_instance = server_instance

    def stop_server(self):
        try:
            self.server_instance.stop()
            self.finished.emit()
        except Exception as e:
            self.error.emit(f"Failed to stop server: {e}")
            self.finished.emit()
