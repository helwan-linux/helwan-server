from PyQt5.QtWidgets import (
    QMainWindow, QApplication, QVBoxLayout, QWidget, QPushButton, QLabel,
    QHBoxLayout, QFileDialog, QMessageBox, QLineEdit,
    QTextEdit, QComboBox, QGroupBox, QFormLayout, QAction
)
from PyQt5.QtGui import QIcon, QPixmap, QDesktopServices
from PyQt5.QtCore import Qt, QSize, QUrl, pyqtSignal, QThread

import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from server_manager.web_server import WebServer, ServerStopper, ServerStarter
from server_manager.config import DEFAULT_PORT, SERVER_TYPES

# تعريف المسار المطلق المتوقع للأيقونة بعد التثبيت
# يجب أن يتطابق هذا مع المسار الذي ينسخ إليه PKGBUILD الأيقونة
INSTALLED_ICON_PATH = "/usr/share/icons/hicolor/256x256/apps/hel-web-server.png"

class MainWindow(QMainWindow):
    log_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Hel-Web-Server")
        self.setFixedSize(700, 600)

        self.set_window_icon()

        self.server = WebServer(port=DEFAULT_PORT, log_signal=self.log_signal)

        self.selected_folder = ""

        # تهيئة متغيرات QThread و Workers
        self.stop_thread = None
        self.stop_worker = None
        self.start_thread = None
        self.start_worker = None

        self.init_ui()
        self.log_signal.connect(self.append_log)
        self.update_ui_state()

    def set_window_icon(self):
        """
        Sets the window icon for the application.
        يبحث عن الأيقونة في المسار المثبت أولاً، ثم في المسار النسبي للتطوير.
        """
        icon_found = False
        
        # 1. حاول البحث عن الأيقونة في المسار المطلق بعد التثبيت
        if os.path.exists(INSTALLED_ICON_PATH):
            self.setWindowIcon(QIcon(INSTALLED_ICON_PATH))
            icon_found = True
        else:
            # 2. إذا لم يتم العثور عليها، حاول البحث في المسار النسبي (للتطوير المحلي)
            # افترض أن 'main_window.py' موجود في 'gui/' وأن 'icon.png' في 'gui/resources/'
            relative_icon_path = os.path.join(os.path.dirname(__file__), "resources", "icon.png")
            if os.path.exists(relative_icon_path):
                self.setWindowIcon(QIcon(relative_icon_path))
                icon_found = True
            
        if not icon_found:
            # يمكنك إضافة طباعة تحذير هنا إذا أردت، ولكن الكود الأصلي كان يتجاهل ذلك
            pass # لا تطبع رسائل إذا لم يتم العثور على الأيقونة
        
    def init_ui(self):
        """
        Initializes all UI elements and lays them out.
        """
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout()

        # إنشاء شريط القوائم (MenuBar)
        menubar = self.menuBar()

        # إنشاء قائمة "مساعدة" (Help Menu)
        help_menu = menubar.addMenu('Help')

        # إضافة إجراء "شرح استخدام البرنامج" (Help Content Action)
        help_action = QAction('Help Content', self)
        help_action.triggered.connect(self.show_help_dialog)
        help_menu.addAction(help_action)

        # إضافة فاصل بين الخيارات
        help_menu.addSeparator()

        # إضافة إجراء "حول البرنامج" (About Action)
        about_action = QAction('About', self)
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)

        # 1. Folder & Port Selection Group
        settings_group = QGroupBox("Server Settings")
        settings_layout = QFormLayout()

        # Folder selection
        folder_selection_layout = QHBoxLayout()
        self.folder_label = QLabel("No project folder selected.")
        self.folder_label.setWordWrap(True)
        folder_selection_layout.addWidget(self.folder_label, 1)

        select_folder_button = QPushButton("Select Folder")
        select_folder_button.clicked.connect(self.select_folder)
        folder_selection_layout.addWidget(select_folder_button)

        open_folder_button = QPushButton("Open Folder")
        open_folder_button.clicked.connect(self.open_selected_folder)
        open_folder_button.setEnabled(False)
        self.open_folder_button = open_folder_button
        folder_selection_layout.addWidget(open_folder_button)

        settings_layout.addRow("Project Folder:", folder_selection_layout)

        # Port input
        self.port_input = QLineEdit(str(DEFAULT_PORT))
        self.port_input.setPlaceholderText("Enter port number (e.g., 8000)")
        self.port_input.setFixedWidth(100)
        settings_layout.addRow("Port:", self.port_input)

        # Server Type selection
        self.server_type_combo = QComboBox()
        # إضافة المفاتيح (الأسماء المعروضة) إلى القائمة المنسدلة
        self.server_type_combo.addItems(SERVER_TYPES.keys())
        settings_layout.addRow("Server Type:", self.server_type_combo)

        settings_group.setLayout(settings_layout)
        main_layout.addWidget(settings_group)


        # 2. Server Control Buttons Group
        control_group = QGroupBox("Server Control")
        server_control_layout = QHBoxLayout()

        self.start_button = QPushButton("Start Server")
        self.start_button.setEnabled(False)
        self.start_button.clicked.connect(self.start_server_clicked)
        server_control_layout.addWidget(self.start_button)

        self.stop_button = QPushButton("Stop Server")
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stop_server_clicked)
        server_control_layout.addWidget(self.stop_button)

        control_group.setLayout(server_control_layout)
        main_layout.addWidget(control_group)

        # 3. Server Status and Address
        status_address_group = QGroupBox("Server Status")
        status_address_layout = QVBoxLayout()

        self.status_label = QLabel("Status: Stopped")
        status_address_layout.addWidget(self.status_label)

        self.address_label = QLabel("Address: Not Available")
        self.address_label.setTextInteractionFlags(Qt.TextBrowserInteraction)
        # لا نربط هنا بشكل مباشر لأنه يمكن أن يكون هناك أكثر من رابط
        status_address_layout.addWidget(self.address_label)

        status_address_group.setLayout(status_address_layout)
        main_layout.addWidget(status_address_group)

        # 4. Logging Area
        log_group = QGroupBox("Server Logs")
        log_layout = QVBoxLayout()
        self.log_text_edit = QTextEdit()
        self.log_text_edit.setReadOnly(True)
        log_layout.addWidget(self.log_text_edit)
        log_group.setLayout(log_layout)
        main_layout.addWidget(log_group, 1)

        central_widget.setLayout(main_layout)
        self.update_ui_state()

    def select_folder(self):
        """
        Opens a dialog to select the project folder.
        """
        folder = QFileDialog.getExistingDirectory(self, "Select Project Folder", os.path.expanduser("~"))
        if folder:
            self.selected_folder = folder
            self.folder_label.setText(f"Project Folder: {self.selected_folder}")
            self.update_ui_state()
        else:
            self.update_ui_state()

    def open_selected_folder(self):
        """
        Opens the currently selected project folder in the default file manager.
        """
        if self.selected_folder and os.path.exists(self.selected_folder):
            try:
                QDesktopServices.openUrl(QUrl.fromLocalFile(self.selected_folder))
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not open folder: {e}")
        else:
            QMessageBox.warning(self, "Warning", "No valid folder selected to open.")

    def start_server_clicked(self):
        """
        Handles the 'Start Server' button click, running the server start in a separate thread.
        """
        if not self.selected_folder:
            QMessageBox.warning(self, "Error", "Please select a project folder first.")
            return

        try:
            port = int(self.port_input.text())
            if not (1024 <= port <= 65535):
                QMessageBox.warning(self, "Invalid Port", "Port number must be between 1024 and 65535.")
                return
        except ValueError:
            QMessageBox.warning(self, "Invalid Port", "Please enter a valid number for the port.")
            return

        selected_display_name = self.server_type_combo.currentText()
        server_type_id = SERVER_TYPES.get(selected_display_name)

        self.append_log(f"Attempting to start '{selected_display_name}' server on port {port} from {self.selected_folder}")

        # تهيئة QThread و Worker لبدء الخادم
        self.start_thread = QThread()
        self.start_worker = ServerStarter(self.server, self.selected_folder, port, server_type_id)
        self.start_worker.moveToThread(self.start_thread)

        # ربط الإشارات (signals)
        self.start_thread.started.connect(self.start_worker.start_server)
        self.start_worker.finished.connect(self.on_server_started)
        self.start_worker.error.connect(self.on_server_start_error)
        self.start_worker.finished.connect(self.start_thread.quit) # إيقاف الـ thread بعد انتهاء الـ worker
        self.start_worker.deleteLater() # حذف الـ worker عندما لا يكون مطلوبًا بعد الآن
        self.start_thread.finished.connect(self.start_thread.deleteLater) # حذف الـ thread عندما ينتهي

        # تعطيل الأزرار أثناء عملية البدء
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        self.port_input.setEnabled(False)
        self.server_type_combo.setEnabled(False)
        self.append_log("Starting server in background...")

        self.start_thread.start()

    def on_server_started(self, success):
        """
        تُستدعى بعد انتهاء محاولة بدء الخادم.
        """
        self.update_ui_state() # لتحديث حالة الأزرار والعناوين بعد انتهاء العملية

        if success:
            pass
        # رسالة الخطأ يتم التعامل معها بواسطة on_server_start_error

    def on_server_start_error(self, message):
        """
        تُستدعى في حالة حدوث خطأ أثناء بدء الخادم.
        """
        QMessageBox.critical(self, "Server Start Error", message)
        self.update_ui_state() # تحديث الواجهة الرسومية حتى لو فشلت العملية

    def stop_server_clicked(self):
        """
        Handles the 'Stop Server' button click, running the server stop in a separate thread.
        """
        if not self.server.is_running():
            QMessageBox.warning(self, "Warning", "Server is not running.")
            self.update_ui_state()
            return

        self.append_log("Attempting to stop server in background...")

        # تعطيل زر الإيقاف لمنع النقرات المتعددة أثناء العملية
        self.stop_button.setEnabled(False)
        self.start_button.setEnabled(False)

        # تهيئة QThread و Worker لإيقاف الخادم
        self.stop_thread = QThread()
        self.stop_worker = ServerStopper(self.server)
        self.stop_worker.moveToThread(self.stop_thread)

        # ربط الإشارات (signals)
        self.stop_thread.started.connect(self.stop_worker.stop_server)
        self.stop_worker.finished.connect(self.on_server_stopped)
        self.stop_worker.error.connect(self.on_server_stop_error)
        self.stop_worker.finished.connect(self.stop_thread.quit) # إيقاف الـ thread بعد انتهاء الـ worker
        self.stop_worker.deleteLater() # حذف الـ worker عندما لا يكون مطلوبًا بعد الآن
        self.stop_thread.finished.connect(self.stop_thread.deleteLater) # حذف الـ thread عندما ينتهي

        self.stop_thread.start()

    def on_server_stopped(self):
        """
        تُستدعى بعد انتهاء عملية إيقاف الخادم.
        """
        self.update_ui_state() # تحديث الواجهة الرسومية تلقائيًا بناءً على حالة الخادم الفعلية
        # رسالة "تم إيقاف الخادم بنجاح" يتم إرسالها من Worker نفسه في web_server.py

    def on_server_stop_error(self, message):
        """
        تُستدعى في حالة حدوث خطأ أثناء إيقاف الخادم.
        """
        QMessageBox.critical(self, "Server Stop Error", message)
        self.update_ui_state() # تحديث الواجهة الرسومية حتى لو فشلت العملية


    def update_ui_state(self):
        """
        Updates the state of UI elements based on server status and folder selection.
        """
        is_running = self.server.is_running()
        has_folder = bool(self.selected_folder)

        # تمكين/تعطيل الأزرار بناءً على حالة الخادم واختيار المجلد
        self.start_button.setEnabled(not is_running and has_folder)
        self.stop_button.setEnabled(is_running)
        self.open_folder_button.setEnabled(has_folder)

        self.port_input.setEnabled(not is_running)
        self.server_type_combo.setEnabled(not is_running)

        if is_running:
            self.status_label.setText(f"Status: Running (Port: {self.server.port}, Type: {self.server.server_type})")
            
            # عرض روابط متعددة (localhost و IP)
            addresses = self.server.get_local_and_ip_addresses()
            if addresses:
                address_html = "<b>Access Server:</b><br>"
                # عرض localhost أولاً
                address_html += f'Local (This PC): <a href="{addresses[0]}">{addresses[0]}</a><br>'
                # عرض عنوان IP المحلي إذا كان مختلفًا
                if len(addresses) > 1 and addresses[0] != addresses[1]:
                    address_html += f'Network (Other Devices): <a href="{addresses[1]}">{addresses[1]}</a>'
                else: # في حالة أن الـ IP المحلي هو نفسه localhost (مثل عندما لا يكون هناك اتصال بالشبكة)
                    address_html += f'Network: <a href="{addresses[0]}">{addresses[0]}</a> (Same as Local)'

                self.address_label.setText(address_html.strip())
            else:
                self.address_label.setText("Address: Not Available")
            
            # ربط open_link بـ address_label فقط عند الحاجة، لأنه يمكن أن يكون هناك روابط متعددة
            self.address_label.linkActivated.connect(self.open_link)
        else:
            self.status_label.setText("Status: Stopped")
            self.address_label.setText("Address: Not Available")

    def open_link(self, link):
        """
        Opens a given URL in the default web browser.
        """
        QDesktopServices.openUrl(QUrl(link))

    def append_log(self, message):
        """
        Appends a message to the log text edit area.
        """
        self.log_text_edit.append(message)
        self.log_text_edit.verticalScrollBar().setValue(self.log_text_edit.verticalScrollBar().maximum())

    def closeEvent(self, event):
        """
        Handles the window close event to ensure the server is stopped and threads are properly terminated.
        This version is non-blocking for a smoother exit.
        """
        # إذا كان الخادم يعمل، اسأل المستخدم إذا أراد إيقافه
        if self.server.is_running():
            reply = QMessageBox.question(self, 'Stop Server?',
                                         "The server is still running. Do you want to stop it before closing?",
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
            if reply == QMessageBox.No:
                event.ignore() # إذا اختار المستخدم لا، لا تغلق التطبيق
                return

            # إذا اختار المستخدم نعم، أو إذا لم يكن الخادم يعمل أصلاً
            # نستخدم try-except للتعامل بأمان مع حالة أن الـ thread قد يكون تم حذفه
            stop_thread_is_running = False
            if self.stop_thread is not None:
                try:
                    stop_thread_is_running = isinstance(self.stop_thread, QThread) and self.stop_thread.isRunning()
                except RuntimeError:
                    # إذا حدث هذا الخطأ، فهذا يعني أن الكائن قد تم حذفه بالفعل.
                    # نعتبره غير قيد التشغيل ونمضي قدمًا.
                    stop_thread_is_running = False
                    self.stop_thread = None # إعادة تعيينه لتجنب محاولات الوصول المستقبلية

            if not stop_thread_is_running: # إذا لم يكن الـ thread قيد التشغيل أو كان محذوفًا
                self.stop_thread = QThread()
                self.stop_worker = ServerStopper(self.server)
                self.stop_worker.moveToThread(self.stop_thread)

                # ربط الإشارات: عند بدء الـ thread، ابدأ العامل (worker)
                self.stop_thread.started.connect(self.stop_worker.stop_server)
                
                # ربط إشارة انتهاء Worker بإنهاء الـ thread
                self.stop_worker.finished.connect(self.stop_thread.quit) 
                
                # تنظيف الـ workers والـ threads
                self.stop_worker.deleteLater() 
                self.stop_thread.finished.connect(self.stop_thread.deleteLater) 
                
                self.append_log("Initiating background server stop. Application will close when finished.")
                self.stop_thread.start() 

                # الآن نسمح لـ closeEvent بالانتهاء فورًا،
                # ونتوقع أن يتم إغلاق التطبيق بواسطة إشارة 'finished' من stop_worker (إذا قمت بربطها بـ QApplication.instance().quit في مكان آخر)
                event.accept() 
                return 

            else:
                # هذا السيناريو (Thread الإيقاف يعمل بالفعل) يجب أن يكون نادرًا عند الإغلاق المباشر
                # إذا كان الخيط يعمل بالفعل، اسمح بالإغلاق، وافترض أنه سينهي نفسه لاحقًا
                event.accept()
                return

        # إذا لم يكن السيرفر يعمل، أو إذا اختار المستخدم عدم إيقافه ووافقنا على الإغلاق
        # التعامل مع QThread الخاص بالبدء (تنظيف احتياطي)
        if self.start_thread is not None:
            # تحقق مما إذا كان الكائن لا يزال QThread وصالحًا
            try:
                if isinstance(self.start_thread, QThread) and self.start_thread.isRunning():
                    self.start_thread.quit() 
                    self.start_thread.wait(5000) # انتظر بحد أقصى 5 ثوانٍ
            except RuntimeError:
                pass # تجاهل الخطأ إذا حدث أثناء التنظيف (قد يكون تم حذفه بالفعل)
            # بغض النظر عما إذا كان يعمل أو لا، قم بتنظيف المراجع
            self.start_thread = None
            self.start_worker = None

        # خطوة أخيرة للتأكد من إيقاف الخادم الرئيسي (كإجراء احتياطي إذا لم يتم إيقافه بالـ thread)
        if self.server.is_running() and self.server.httpd:
            self.server.log_signal.emit("Attempting to force stop server before exiting.")
            try:
                self.server.httpd.shutdown()
                self.server.httpd.server_close()
                if self.server.server_thread and self.server.server_thread.is_alive():
                    self.server.server_thread.join(timeout=5)
            except Exception as e:
                self.server.log_signal.emit(f"Error during force stop: {e}")
            finally:
                self.server.httpd = None
                self.server.server_thread = None

        event.accept()

    def show_help_dialog(self):
        """
        Displays a help dialog with instructions on how to use the server.
        """
        help_text = """
        <h3>Hel-Web-Server Usage Instructions:</h3>
        <p>This application allows you to quickly start a local web server to serve files from a selected folder.</p>
        
        <h4>1. Server Settings:</h4>
        <ul>
            <li><b>Project Folder:</b> Click "Select Folder" to choose the directory containing your web files (HTML, CSS, JS, images, etc.).</li>
            <li><b>Open Folder:</b> Opens the currently selected project folder in your system's file explorer.</li>
            <li><b>Port:</b> Enter the port number for the server. Common choices are 8000, 5500, etc. (Ports below 1024 often require administrator privileges).</li>
            <li><b>Server Type:</b> Select the type of server. This typically corresponds to different Python modules (e.g., http.server, SimpleHTTPServer).</li>
        </ul>
        
        <h4>2. Server Control:</h4>
        <ul>
            <li><b>Start Server:</b> Starts the web server using the selected folder, port, and server type.</li>
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
        """
        Displays an about dialog for the application.
        """
        about_text = """
        <h3>About Hel-Web-Server</h3>
        <p>Version: 1.0.0</p>
        <p>Developed by: Saeed Badrelden</p>
        <p>Hel-Web-Server is a simple local web server utility built with PyQt5.</p>
        <p>Designed to help web developers quickly serve static files for testing purposes.</p>
        <p>Copyright © 2025</p>
        """
        QMessageBox.about(self, "About Hel-Web-Server", about_text)
