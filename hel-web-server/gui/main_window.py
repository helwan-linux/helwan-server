from PyQt5.QtWidgets import (
    QMainWindow, QApplication, QVBoxLayout, QWidget, QPushButton, QLabel,
    QHBoxLayout, QFileDialog, QMessageBox, QLineEdit,
    QTextEdit, QComboBox, QGroupBox, QFormLayout, QAction
)
from PyQt5.QtGui import QIcon, QPixmap, QDesktopServices, QIntValidator
from PyQt5.QtCore import Qt, QSize, QUrl, pyqtSignal, QThread

import os
import sys
import socket
import time # 👈🏻 تم إصلاح الخطأ NameError: name 'time' is not defined
from PyQt5.QtGui import QIntValidator 


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
        self.update_status_display(False) 
        
        self.server.log_signal.connect(self.update_logs)
        self.server.server_started.connect(self.update_status_display)
        
        self.populate_server_types()

    # ----------------------------------------------------------------------
    # UI Setup & Configuration
    # ----------------------------------------------------------------------

    def set_window_icon(self):
        """Sets the window icon based on environment."""
        if os.path.exists(INSTALLED_ICON_PATH):
            self.setWindowIcon(QIcon(INSTALLED_ICON_PATH))
        else:
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
        self.port_input.setValidator(QIntValidator(1025, 65535, self))

        self.server_type_combo = QComboBox() 

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
        
        self.create_menus() 

    def populate_server_types(self): 
        """Fills the server type dropdown with supported server names."""
        self.server_type_combo.clear()
        for name in SERVER_TYPES.keys():
            self.server_type_combo.addItem(name)

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
            pass 

    def start_server_thread(self):
        """Prepares to start the server in a separate thread."""
        if self.is_server_running:
            QMessageBox.warning(self, "Warning", "Server is already running.")
            return

        project_path = self.selected_folder
        port = self.current_port
        server_type_name = self.server_type_combo.currentText()
        server_type_id = SERVER_TYPES.get(server_type_name)

        if not project_path or not server_type_id:
            QMessageBox.critical(self, "Error", "Please select a valid folder and server type.")
            return

        self.log_display.clear()
        self.update_logs(f"Starting server in thread... Project: {project_path}, Port: {port}, Type: {server_type_name}")

        self.thread = QThread()
        self.worker = ServerStarter(self.server, project_path, port, server_type_id)
        
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.start_server)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.worker.error.connect(self.handle_server_error)
        
        self.thread.start()
        
        # تعطيل كلا الزرين حتى تأتي إشارة النجاح من الخادم
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(False)


    def stop_server_thread(self):
        """Stops the server in a separate thread."""
        if not self.is_server_running:
            QMessageBox.warning(self, "Warning", "Server is not running.")
            return

        self.update_logs("Stopping server in thread...")
        
        self.stop_thread = QThread()
        self.stop_worker = ServerStopper(self.server)
        
        self.stop_worker.moveToThread(self.stop_thread)
        self.stop_thread.started.connect(self.stop_worker.stop_server)
        self.stop_worker.finished.connect(self.stop_thread.quit)
        self.stop_worker.finished.connect(self.stop_worker.deleteLater)
        self.stop_thread.finished.connect(self.stop_thread.deleteLater)
        self.stop_worker.error.connect(self.handle_server_error)
        
        self.stop_thread.start()
        
        # تعطيل الأزرار أثناء عملية الإيقاف
        self.start_button.setEnabled(False) 
        self.stop_button.setEnabled(False) 

    def handle_server_error(self, message):
        """Handles and displays server-related errors."""
        QMessageBox.critical(self, "Server Error", message)
        self.update_logs(f"[FATAL ERROR]: {message}")
        self.update_status_display(False) 

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
        
        # تفعيل وتعطيل الأزرار بناءً على الحالة الواردة من الخادم
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
    
    def create_menus(self):
        """Creates the application menu bar (File, Help)."""
        menu_bar = self.menuBar()

        # File Menu
        file_menu = menu_bar.addMenu("File")
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Help Menu
        help_menu = menu_bar.addMenu("Help")
        help_action = QAction("Help", self)
        help_action.triggered.connect(self.show_help_dialog)
        help_menu.addAction(help_action)
        
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)

    def show_help_dialog(self):
        """Displays a help dialog with instructions."""
        help_text = """
        <h3>Hel-Web-Server Help</h3>
        <p>This application is a simple GUI tool to manage various local web servers for development.</p>

        <h4>1. Server Settings:</h4>
        <ul>
            <li><b>Project Folder:</b> Select the root directory of your project (where <code>index.html</code>, <code>manage.py</code>, <code>app.py</code>, or <code>index.php</code> resides).</li>
            <li><b>Port:</b> Specify the port number (e.g., 8000) for the server to listen on.</li>
            <li><b>Server Type:</b> Choose the appropriate server type for your project:
                <ul>
                    <li>Static Files (Python http.server): For HTML, CSS, JavaScript.</li>
                    <li>Flask Application: For simple Python web apps (requires <code>app.py</code>).</li>
                    <li>Django Application: For Django projects (requires <code>manage.py</code>).</li>
                    <li>PHP Built-in Server: For PHP projects (requires PHP CLI in PATH).</li>
                </ul>
            </li>
        </ul>
        
        <h4>2. Actions:</h4>
        <ul>
            <li><b>Start Server:</b> Initializes and runs the selected server type in a background thread.</li>
            <li><b>Stop Server:</b> Terminates the currently running web server.</li>
        </ul>
        
        <h4>3. Server Status:</h4>
        <ul>
            <li><b>Status:</b> Shows whether the server is running or stopped.</li>
            <li><b>Address:</b> Displays the local address and network IP address as clickable links.</li>
        </ul>
        
        <h4>4. Server Logs:</h4>
        <p>This area displays messages and errors from the server.</p>
        
        <p><b>Important:</b> If the server does not start, ensure dependencies are installed and the port is free.</p>
        """
        QMessageBox.information(self, "Hel-Web-Server Help", help_text)

    def show_about_dialog(self):
        """Displays an about dialog for the application."""
        about_text = """
        <h3>About Hel-Web-Server</h3>
        <p>Version: 1.0.0 (Final Corrected)</p>
        <p>Developed to centralize local web development servers (Python, PHP, Static).</p>
        """
        QMessageBox.information(self, "Hel-Web-Server About", about_text)
