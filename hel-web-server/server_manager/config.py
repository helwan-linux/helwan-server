# server_manager/config.py
DEFAULT_PORT = 8000

# أنواع الخوادم المدعومة.
# المفتاح هو الاسم المعروض في الواجهة، والقيمة هي المعرف الداخلي
# أو أي بيانات تعريف إضافية تحتاجها للتمييز بينها.
SERVER_TYPES = {
    "Static Files (Python http.server)": "http.server",
    "Flask Application": "flask",
    "Django Application": "django",
    "PHP Built-in Server": "php_server",
}
