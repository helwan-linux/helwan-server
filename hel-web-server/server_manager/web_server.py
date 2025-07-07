
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
        if log_signal:
            self.log_signal = log_signal # نربط الإشارة الموجودة في main_window

    def is_running(self):
        return self.httpd is not None and self.server_thread and self.server_thread.is_alive()

    def get_local_and_ip_addresses(self):
        addresses = []
        try:
            local_ip = "127.0.0.1"
            hostname = socket.gethostname()
            ip_address = socket.gethostbyname(hostname)

            addresses.append(f"http://{local_ip}:{self.port}")
            if ip_address != local_ip:
                addresses.append(f"http://{ip_address}:{self.port}")
        except Exception as e:
            self.log_signal.emit(f"Error getting network addresses: {e}")
        return addresses

    def start(self, project_path, port, server_type_id):
        self.project_path = project_path
        self.port = port
        self.server_type = SERVER_TYPES.get(server_type_id, "Unknown") # احصل على اسم العرض

        if self.is_running():
            self.log_signal.emit("Server is already running.")
            self.server_started.emit(False)
            return

        # تحقق من توفر المنفذ قبل البدء
        if not self._is_port_available(self.port):
            self.log_signal.emit(f"Error: Port {self.port} is already in use.")
            self.server_started.emit(False)
            return False

        try:
            if server_type_id == "http.server":
                self.log_signal.emit(f"Starting standard HTTP server at {self.project_path} on port {self.port}...")
                Handler = http.server.SimpleHTTPRequestHandler
                # لتغيير المجلد الحالي لـ http.server
                os.chdir(self.project_path)
                self.httpd = socketserver.TCPServer(("", self.port), Handler)
                self.server_thread = threading.Thread(target=self.httpd.serve_forever)
                self.server_thread.daemon = True # يجعل الـ thread يتوقف عند إغلاق البرنامج الرئيسي
                self.server_thread.start()
                self.log_signal.emit(f"HTTP Server started successfully on port {self.port}.")

            elif server_type_id == "flask":
                self.log_signal.emit(f"Starting Flask application at {self.project_path} on port {self.port}...")
                flask_app_path = os.path.join(self.project_path, 'app.py')
                if not os.path.exists(flask_app_path):
                    raise FileNotFoundError(f"Flask app.py not found in {self.project_path}")

                # تشغيل Flask باستخدام subprocess
                # يجب أن نضمن أن Flask تعرف مكان app.py
                env = os.environ.copy()
                env['FLASK_APP'] = flask_app_path
                env['FLASK_RUN_PORT'] = str(self.port)
                env['FLASK_RUN_HOST'] = '0.0.0.0' # لجعلها متاحة من الشبكة
                
                # استخدام subprocess.Popen لتشغيل Flask في الخلفية
                # shell=True يمكن أن يكون خطيرًا، لكنه يبسط التشغيل هنا
                # stdout و stderr لعدم عرض مخرجات Flask في terminal التطبيق
                self.flask_process = subprocess.Popen(
                    [sys.executable, "-m", "flask", "run"],
                    cwd=self.project_path, # تشغيل من مجلد المشروع
                    env=env,
                    stdout=subprocess.PIPE, # التقاط الإخراج القياسي
                    stderr=subprocess.PIPE, # التقاط أخطاء Flask
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0 # لا تظهر نافذة terminal إضافية على ويندوز
                )
                self.httpd = True # مجرد علم بأن السيرفر "يعمل" (عملية flask)
                self.server_thread = threading.Thread(target=self._monitor_flask_process)
                self.server_thread.daemon = True
                self.server_thread.start()
                self.log_signal.emit(f"Flask application started successfully on port {self.port}.")

            elif server_type_id == "django":
                self.log_signal.emit(f"Starting Django application at {self.project_path} on port {self.port}...")
                manage_py_path = os.path.join(self.project_path, 'manage.py')
                if not os.path.exists(manage_py_path):
                    raise FileNotFoundError(f"Django manage.py not found in {self.project_path}")

                # تشغيل Django باستخدام subprocess
                self.django_process = subprocess.Popen(
                    [sys.executable, manage_py_path, "runserver", f"0.0.0.0:{self.port}"],
                    cwd=self.project_path,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                )
                self.httpd = True # مجرد علم بأن السيرفر "يعمل" (عملية django)
                self.server_thread = threading.Thread(target=self._monitor_django_process)
                self.server_thread.daemon = True
                self.server_thread.start()
                self.log_signal.emit(f"Django application started successfully on port {self.port}.")

            else:
                raise ValueError("Unsupported server type specified.")

            self.server_started.emit(True)
            return True

        except FileNotFoundError as e:
            self.log_signal.emit(f"Error: {e}. Please ensure the project structure is correct for the selected server type.")
            self.server_started.emit(False)
            return False
        except Exception as e:
            self.log_signal.emit(f"Error starting server: {e}")
            self.httpd = None # تأكد من أن الحالة هي "متوقف" في حالة الفشل
            self.server_started.emit(False)
            return False

    def stop(self):
        if not self.is_running():
            self.log_signal.emit("Server is not running.")
            return

        if self.server_type == "http.server" and self.httpd:
            self.log_signal.emit("Stopping standard HTTP server...")
            self.httpd.shutdown()
            self.httpd.server_close()
            self.server_thread.join(timeout=2) # انتظر قليلاً حتى ينتهي الـ thread
            self.log_signal.emit("HTTP Server stopped successfully.")
        
        elif self.server_type == "flask" and hasattr(self, 'flask_process') and self.flask_process.poll() is None:
            self.log_signal.emit("Stopping Flask application...")
            # Flask لا يوفر طريقة إيقاف أنيقة عبر subprocess، نضطر لإنهاء العملية
            self.flask_process.terminate()
            self.flask_process.wait(timeout=5) # انتظر حتى تنتهي العملية
            if self.flask_process.poll() is None: # إذا لم تنتهِ، اقتلها
                self.flask_process.kill()
            self.log_signal.emit("Flask application stopped.")

        elif self.server_type == "django" and hasattr(self, 'django_process') and self.django_process.poll() is None:
            self.log_signal.emit("Stopping Django application...")
            # Django لا يوفر طريقة إيقاف أنيقة عبر subprocess، نضطر لإنهاء العملية
            self.django_process.terminate()
            self.django_process.wait(timeout=5) # انتظر حتى تنتهي العملية
            if self.django_process.poll() is None: # إذا لم تنتهِ، اقتلها
                self.django_process.kill()
            self.log_signal.emit("Django application stopped.")
        
        else:
            self.log_signal.emit("Unknown server type or process not found. Attempting generic cleanup.")

        self.httpd = None
        self.server_thread = None
        # إعادة المجلد الحالي إلى مجلد البرنامج الأصلي بعد إيقاف http.server
        # (فقط إذا كنا قد غيرناه)
        if self.server_type == "http.server" and self.project_path:
            os.chdir(os.path.dirname(os.path.abspath(__file__))) # العودة إلى مجلد server_manager
            os.chdir("..") # ثم العودة إلى المجلد الرئيسي للمشروع


    def _is_port_available(self, port):
        """
        Checks if a given port is available.
        """
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return True
            except OSError:
                return False

    def _monitor_flask_process(self):
        """Monitors the Flask subprocess output."""
        if hasattr(self, 'flask_process') and self.flask_process:
            for line in iter(self.flask_process.stderr.readline, b''):
                self.log_signal.emit(f"[Flask]: {line.decode().strip()}")
            self.flask_process.stderr.close()
            # Once the process ends, update status
            self.log_signal.emit("Flask process terminated.")
            self.httpd = None # Mark as stopped
            self.server_thread = None

    def _monitor_django_process(self):
        """Monitors the Django subprocess output."""
        if hasattr(self, 'django_process') and self.django_process:
            for line in iter(self.django_process.stderr.readline, b''):
                self.log_signal.emit(f"[Django]: {line.decode().strip()}")
            self.django_process.stderr.close()
            # Once the process ends, update status
            self.log_signal.emit("Django process terminated.")
            self.httpd = None # Mark as stopped
            self.server_thread = None

# Workers for QThreads (same as before, just included for completeness)
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
