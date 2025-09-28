from PyQt5.QtWidgets import (
    QMainWindow, QApplication, QVBoxLayout, QWidget, QPushButton, QLabel,
    QHBoxLayout, QFileDialog, QMessageBox, QLineEdit,
    QTextEdit, QComboBox, QGroupBox, QFormLayout, QAction
)
from PyQt5.QtGui import QIcon, QPixmap, QDesktopServices
from PyQt5.QtCore import Qt, QSize, QUrl, pyqtSignal, QThread

import os
import sys
import socket
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from server_manager.web_server import WebServer, ServerStopper, ServerStarter
from server_manager.config import DEFAULT_PORT, SERVER_TYPES

# تعريف المسار المطلق المتوقع للأيقونة بعد التثبيت
INSTALLED_ICON_PATH = "/usr/share/icons/hicolor/256x256/apps/hel-web-server.png"

class MainWindow(QMainWindow):
    log_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Hel-Web-Server")
        self.setFixedSize(700, 600)

        self.set_window_icon()

        self.server = WebServer(port=DEFAULT_PORT, log_signal=self.log_signal)
        self.selected_folder = os.getcwd()
        self.current_port = DEFAULT_PORT
        self.is_server_running = False

        self.setup_ui()
        self.setup_connections()
        self.update_status_display(False) # إعداد الحالة الابتدائية
        
        # ربط الإشارة بالدالة التي تقوم بعرض السجلات
        self.server.log_signal.connect(self.update_logs)
        self.server.server_started.connect(self.update_status_display)
        
        # تعبئة قائمة أنواع الخوادم بعد تهيئة الـ QComboBox
        self.populate_server_types()

    # ----------------------------------------------------------------------
    # UI Setup & Configuration
    # ----------------------------------------------------------------------

    def set_window_icon(self):
        """Sets the window icon based on environment."""
        # محاولة تحميل الأيقونة من المسار المطلق (للتثبيت)
        if os.path.exists(INSTALLED_ICON_PATH):
            self.setWindowIcon(QIcon(INSTALLED_ICON_PATH))
        else:
            # محاولة تحميل الأيقونة من المسار النسبي (للتطوير)
            icon_path = os.path.join(os.path.dirname(__file__), 'resources', 'icon.png')
            if os.path.exists(icon_path):
                 self.setWindowIcon(QIcon(icon_path))

    def setup_ui(self):
        """Sets up the main structure of the user interface."""
        main_widget = QWidget()
        main_layout = QVBoxLayout()
        
        # 1. إعدادات الخادم
        settings_group = QGroupBox("Server Settings")
        settings_layout = QFormLayout()
        
        self.folder_label = QLabel(self.selected_folder)
        self.folder_label.setToolTip("Project Path")
        self.browse_button = QPushButton("Browse")
        
        folder_layout = QHBoxLayout()
        folder_layout.addWidget(self.folder_label)
        folder_layout.addWidget(self.browse_button)

        self.port_input = QLineEdit(str(DEFAULT_PORT))
        self.port_input.setFixedWidth(100)
        self.port_input.setAlignment(Qt.AlignCenter)
        self.port_input.setValidator(self.create_port_validator()) # افتراض وجود دالة تحقق

        self.server_type_combo = QComboBox() # 👈🏻 تعريف القائمة المنسدلة

        settings_layout.addRow(QLabel("Project Folder:"), folder_layout)
        settings_layout.addRow(QLabel("Port:"), self.port_input)
        settings_layout.addRow(QLabel("Server Type:"), self.server_type_combo)

        self.start_button = QPushButton("Start Server")
        self.stop_button = QPushButton("Stop Server")
        
        action_layout = QHBoxLayout()
        action_layout.addWidget(self.start_button)
        action_layout.addWidget(self.stop_button)
        settings_layout.addRow(action_layout)

        settings_group.setLayout(settings_layout)
        
        # 2. حالة الخادم
        status_group = QGroupBox("Server Status")
        status_layout = QFormLayout()

        self.status_indicator = QLabel("Stopped")
        self.status_indicator.setStyleSheet("color: red; font-weight: bold;")
        
        self.address_label = QLabel("N/A")
        self.address_label.setOpenExternalLinks(True)

        status_layout.addRow(QLabel("Status:"), self.status_indicator)
        status_layout.addRow(QLabel("Address:"), self.address_label)

        status_group.setLayout(status_layout)

        # 3. السجلات
        logs_group = QGroupBox("Server Logs")
        logs_layout = QVBoxLayout()
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        logs_layout.addWidget(self.log_display)
        logs_group.setLayout(logs_layout)

        # دمج الأجزاء
        main_layout.addWidget(settings_group)
        main_layout.addWidget(status_group)
        main_layout.addWidget(logs_group)
        
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)
        
        self.create_menus() # افتراض وجود دالة لإنشاء القوائم

    def populate_server_types(self): # 👈🏻 الدالة الجديدة لتعبئة القائمة
        """Fills the server type dropdown with supported server names."""
        self.server_type_combo.clear()
        # إضافة جميع أنواع الخوادم من قاموس SERVER_TYPES
        for name in SERVER_TYPES.keys():
            self.server_type_combo.addItem(name)

        # تحديد أول خيار افتراضياً
        if self.server_type_combo.count() > 0:
            self.server_type_combo.setCurrentIndex(0)

    # ----------------------------------------------------------------------
    # Signal Connections
    # ----------------------------------------------------------------------

    def setup_connections(self):
        """Connects UI elements to their respective functions."""
        self.browse_button.clicked.connect(self.select_folder)
        self.start_button.clicked.connect(self.start_server_thread)
        self.stop_button.clicked.connect(self.stop_server_thread)
        self.port_input.textChanged.connect(self.update_port)
        
    # ----------------------------------------------------------------------
    # Business Logic
    # ----------------------------------------------------------------------

    def select_folder(self):
        """Opens a file dialog to select the project folder."""
        # نستخدم QFileDialog.getExistingDirectory للسماح للمستخدم باختيار مجلد
        folder = QFileDialog.getExistingDirectory(self, "Select Project Folder", self.selected_folder)
        if folder:
            self.selected_folder = folder
            self.folder_label.setText(self.selected_folder)
            self.update_logs(f"Selected project folder: {self.selected_folder}")

    def update_port(self, text):
        """Updates the port number from the input field."""
        try:
            self.current_port = int(text)
        except ValueError:
            # يمكن تجاهل هذا إذا كان هناك Validator، لكن الأمان أفضل
            pass 

    def start_server_thread(self):
        """Prepares to start the server in a separate thread."""
        if self.is_server_running:
            QMessageBox.warning(self, "Warning", "Server is already running.")
            return

        project_path = self.selected_folder
        port = self.current_port
        server_type_name = self.server_type_combo.currentText()
        # البحث عن المعرف الداخلي (ID) بناءً على الاسم المعروض
        server_type_id = SERVER_TYPES.get(server_type_name)

        if not project_path:
            QMessageBox.critical(self, "Error", "Please select a project folder.")
            return
            
        if not server_type_id:
            self.update_logs(f"Error: Could not find ID for server type {server_type_name}")
            return

        self.log_display.clear()
        self.update_logs(f"Starting server in thread... Project: {project_path}, Port: {port}, Type: {server_type_name}")

        # إنشاء Thread و Worker
        self.thread = QThread()
        self.worker = ServerStarter(self.server, project_path, port, server_type_id)
        
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.start_server)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.worker.error.connect(self.handle_server_error)
        
        self.thread.start()
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.is_server_running = True


    def stop_server_thread(self):
        """Stops the server in a separate thread."""
        if not self.is_server_running:
            QMessageBox.warning(self, "Warning", "Server is not running.")
            return

        self.update_logs("Stopping server in thread...")
        
        # إنشاء Thread و Worker للإيقاف
        self.stop_thread = QThread()
        self.stop_worker = ServerStopper(self.server)
        
        self.stop_worker.moveToThread(self.stop_thread)
        self.stop_thread.started.connect(self.stop_worker.stop_server)
        self.stop_worker.finished.connect(self.stop_thread.quit)
        self.stop_worker.finished.connect(self.stop_worker.deleteLater)
        self.stop_thread.finished.connect(self.stop_thread.deleteLater)
        self.stop_worker.error.connect(self.handle_server_error)
        
        self.stop_thread.start()
        self.start_button.setEnabled(False) # تعطيل زر البدء مؤقتاً
        self.stop_button.setEnabled(False) # تعطيل زر الإيقاف مؤقتاً
        self.is_server_running = False # سيتم تحديث الحالة النهائية في update_status_display

    def handle_server_error(self, message):
        """Handles and displays server-related errors."""
        QMessageBox.critical(self, "Server Error", message)
        self.update_logs(f"[FATAL ERROR]: {message}")
        self.update_status_display(False) # تأكد من إيقاف العرض بعد الخطأ

    # ----------------------------------------------------------------------
    # UI Updates (Slots)
    # ----------------------------------------------------------------------

    def update_logs(self, message):
        """Appends a new message to the log display."""
        timestamp = time.strftime("[%H:%M:%S]")
        self.log_display.append(f"{timestamp} {message}")
        
    def update_status_display(self, started):
        """Updates the status indicator and address labels."""
        self.is_server_running = started
        self.start_button.setEnabled(not started)
        self.stop_button.setEnabled(started)
        
        if started:
            self.status_indicator.setText("Running")
            self.status_indicator.setStyleSheet("color: green; font-weight: bold;")
            
            addresses = self.server.get_local_and_ip_addresses()
            address_html = "<br>".join([f'<a href="{addr}">{addr}</a>' for addr in addresses])
            self.address_label.setText(address_html)
            self.update_logs(f"Server is LIVE at: {addresses[0]}")
        else:
            self.status_indicator.setText("Stopped")
            self.status_indicator.setStyleSheet("color: red; font-weight: bold;")
            self.address_label.setText("N/A")
            
    # ----------------------------------------------------------------------
    # Helper Methods (Menus, Validators, etc.)
    # ----------------------------------------------------------------------
    
    def create_port_validator(self):
        """Creates a QIntValidator for the port input field."""
        from PyQt5.QtGui import QIntValidator
        return QIntValidator(1025, 65535, self) # المنافذ التي يمكن للمستخدم العادي استخدامها

    def create_menus(self):
        """Creates the menu bar and actions."""
        # File Menu
        file_menu = self.menuBar().addMenu("&File")
        
        select_action = QAction("Select Folder...", self)
        select_action.triggered.connect(self.select_folder)
        file_menu.addAction(select_action)
        
        exit_action = QAction("&Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Help Menu
        help_menu = self.menuBar().addMenu("&Help")
        
        help_action = QAction("&Usage Guide", self)
        help_action.triggered.connect(self.show_help_dialog)
        help_menu.addAction(help_action)
        
        about_action = QAction("&About", self)
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)

    def show_help_dialog(self):
        """Displays a detailed help guide."""
        help_text = """
        <h3>Hel-Web-Server Usage Guide</h3>
        
        <h4>1. Project Folder:</h4>
        <p>Click the <b>Browse</b> button to select the root directory of your web project (where your HTML, PHP, or Django/Flask code resides).</p>
        
        <h4>2. Server Settings:</h4>
        <ul>
            <li><b>Port:</b> Enter the desired port number (e.g., 8000).</li>
            <li><b>Server Type:</b> Select the technology:
                <ul>
                    <li><b>Static Files:</b> For simple HTML/CSS/JS (uses Python's http.server).</li>
                    <li><b>Flask/Django Application:</b> For Python web frameworks (requires correct project structure).</li>
                    <li><b>PHP Built-in Server:</b> For PHP projects (requires PHP CLI installed on your system).</li>
                </ul>
            </li>
            <li><b>Start Server:</b> Runs the selected server type in the background.</li>
            <li><b>Stop Server:</b> Stops the running web server.</li>
        </ul>
        
        <h4>3. Server Status:</h4>
        <ul>
            <li><b>Status:</b> Shows whether the server is running or stopped.</li>
            <li><b>Address:</b> Displays the local address (e.g., http://127.0.0.1:8000) and your network IP address (e.g., http://192.168.1.5:8000) if available. Click on these links to open the server in your default web browser. The network IP allows other devices on your local network to access your server.</li>
        </ul>
        
        <h4>4. Server Logs:</h4>
        <p>This area displays messages and errors from the server, helping you monitor its activity.</p>
        
        <p><b>Important:</b> If the server does not start, ensure the port is not already in use by another application and that you have selected a valid project folder.</p>
        """
        QMessageBox.information(self, "Hel-Web-Server Help", help_text)

    def show_about_dialog(self):
        """Displays an about dialog for the application."""
        about_text = """
        <h3>About Hel-Web-Server</h3>
        <p>Version: 1.0.0 (with PHP Support)</p>
        <p>Developed by: Saeed Badrelden</p>
        <p>Hel-Web-Server is a simple local web server utility built with PyQt5.</p>
        <p>Designed to help web developers quickly serve various project types for testing purposes.</p>
        """
        QMessageBox.information(self, "About Hel-Web-Server", about_text)

    def get_local_and_ip_addresses(self):
        # تم نقل هذا المنطق إلى WebServer لضمان الاتساق (لكنه موجود هنا للاحتياط)
        addresses = []
        try:
            local_ip = "127.0.0.1"
            hostname = socket.gethostname()
            ip_address = socket.gethostbyname(hostname)

            addresses.append(f"http://{local_ip}:{self.current_port}")
            if ip_address != local_ip:
                addresses.append(f"http://{ip_address}:{self.current_port}")
        except socket.error as e:
            self.log_signal.emit(f"Error getting network addresses: {e}")
        return addresses
