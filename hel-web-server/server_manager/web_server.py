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
        self.django_process = None # لعمليات Django/Flask
        self.php_process = None # 👈🏻 جديد: عملية خادم PHP
        if log_signal:
            self.log_signal = log_signal # نربط الإشارة الموجودة في main_window

    def is_running(self):
        if self.httpd is not None and self.server_thread and self.server_thread.is_alive():
            return True
        if self.django_process:
            return True
        if self.php_process:
            return True # 👈🏻 جديد: حالة PHP
        return False
    
    # ... (دوال مساعدة أخرى مثل get_local_and_ip_addresses و _is_port_available) ...
    
    def _get_project_name(self, project_path):
        return os.path.basename(project_path)

    def _is_port_available(self, port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                # نستخدم 0.0.0.0 للاختبار على جميع الواجهات
                s.bind(("0.0.0.0", port))
                return True
            except socket.error:
                return False

    def start(self, project_path, port, server_type_id):
        # 1. إيقاف أي خادم يعمل حالياً
        self.stop() 
        
        # 2. فحص توفر المنفذ
        if not self._is_port_available(port):
            self.log_signal.emit(f"Error: Port {port} is already in use. Please choose another port.")
            self.server_started.emit(False)
            return False

        self.port = port
        self.server_type = server_type_id
        self.project_path = project_path

        self.log_signal.emit(f"Attempting to start server type: {SERVER_TYPES.get(server_type_id, server_type_id)} on port {port}")
        
        if server_type_id == "http.server":
            try:
                os.chdir(project_path)
                Handler = http.server.SimpleHTTPRequestHandler
                self.httpd = socketserver.TCPServer(("", port), Handler)
                self.server_thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
                self.server_thread.start()
                self.log_signal.emit(f"Static File Server running at {self.get_local_and_ip_addresses()[0]}")
                self.server_started.emit(True)
                return True
            except Exception as e:
                self.log_signal.emit(f"Failed to start http.server: {e}")
                self.httpd = None
                self.server_started.emit(False)
                return False

        elif server_type_id == "flask":
            # منطق Flask (افتراضي)
            self.log_signal.emit("Starting Flask Application (assuming 'app.py' or equivalent)...")
            try:
                flask_file = os.path.join(project_path, 'app.py') 
                if not os.path.exists(flask_file) and not os.path.exists(os.path.join(project_path, 'wsgi.py')):
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
                env['FLASK_APP'] = os.path.basename(flask_file) if os.path.exists(flask_file) else os.path.basename(os.path.join(project_path, 'wsgi.py'))

                self.django_process = subprocess.Popen(
                    command,
                    cwd=project_path,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    env=env
                )

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
            # منطق Django (افتراضي)
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

        elif server_type_id == "php_server": # 👈🏻 منطق تشغيل PHP
            self.log_signal.emit("Starting PHP Built-in Server...")
            self.project_path = project_path
            self._run_php_server(port, project_path)
            self.server_started.emit(self.php_process is not None)
            return self.php_process is not None

        else:
            self.log_signal.emit(f"Error: Unknown server type ID: {server_type_id}")
            self.server_started.emit(False)
            return False

    # -----------------------------------------------------------
    # دوال خاصة بخادم PHP
    # -----------------------------------------------------------

    def _run_php_server(self, port, doc_root):
        """Runs the PHP built-in server in a subprocess and monitors its output."""
        try:
            # الأمر: php -S 0.0.0.0:PORT -t DOC_ROOT
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
                bufsize=1, # Line buffering
                universal_newlines=True
            )
            self.log_signal.emit(f"PHP Server running at http://{host}:{port}")
            self.log_signal.emit(f"Document Root: {doc_root}")
            
            # تشغيل مراقبة السجلات في خيط منفصل
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
        try:
            if self.php_process and self.php_process.stdout:
                # قراءة المخرجات القياسية
                for line in iter(self.php_process.stdout.readline, ''):
                    if line:
                        self.log_signal.emit(f"[PHP]: {line.strip()}")

            if self.php_process and self.php_process.stderr:
                # قراءة سجلات الأخطاء والوصول (عادةً ما تظهر سجلات الوصول هنا)
                for line in iter(self.php_process.stderr.readline, ''):
                    if line:
                        self.log_signal.emit(f"[PHP-LOG]: {line.strip()}")

        except Exception as e:
            self.log_signal.emit(f"[PHP Monitor Error]: {e}")
        finally:
            if self.php_process:
                self.php_process.wait() # انتظار انتهاء العملية
                if self.php_process.stdout:
                    self.php_process.stdout.close()
                if self.php_process.stderr:
                    self.php_process.stderr.close()
            
            self.log_signal.emit("PHP process terminated.")
            self.php_process = None

    # -----------------------------------------------------------
    # دوال موجودة (افتراضية)
    # -----------------------------------------------------------

    def _monitor_django_logs(self):
        """Monitors stdout and stderr for Django/Flask process (assuming Django is used for both)."""
        # منطق مراقبة سجلات Django/Flask 
        try:
            for line in self.django_process.stdout:
                self.log_signal.emit(f"[SERVER]: {line.decode().strip()}")
            for line in self.django_process.stderr:
                self.log_signal.emit(f"[SERVER-ERR]: {line.decode().strip()}")
        except Exception as e:
            self.log_signal.emit(f"[Monitor Error]: {e}")
        finally:
            if self.django_process:
                self.django_process.wait()
                self.django_process.stdout.close()
                self.django_process.stderr.close()
                self.log_signal.emit("Django/Flask process terminated.")
                self.django_process = None

    def stop(self):
        """St stops the currently running web server."""
        self.server_started.emit(False)

        # 1. إيقاف http.server
        if self.httpd:
            self.log_signal.emit("Stopping Static File Server...")
            self.httpd.shutdown()
            self.server_thread.join()
            self.httpd = None
            self.server_thread = None
            self.log_signal.emit("Static File Server stopped.")

        # 2. إيقاف عملية Django/Flask
        if self.django_process:
            self.log_signal.emit("Stopping Django/Flask Server...")
            try:
                self.django_process.terminate()
                self.django_process.wait(timeout=5)
            except:
                self.django_process.kill()
            self.django_process = None
            self.log_signal.emit("Django/Flask Server stopped.")
            
        # 3. إيقاف عملية PHP 👈🏻 منطق إيقاف PHP
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


# Workers for QThreads (نفس الدوال المساعدة الأصلية)
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
