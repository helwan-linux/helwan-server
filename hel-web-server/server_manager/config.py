# server_manager/config.py
DEFAULT_PORT = 8000

# أنواع الخوادم المدعومة.
# المفتاح هو الاسم المعروض في الواجهة، والقيمة هي المعرف الداخلي
# أو أي بيانات تعريف إضافية تحتاجها للتمييز بينها.
SERVER_TYPES = {
    "Static Files (Python http.server)": "http.server", # تم تغيير الاسم المعروض والمعرف
    "Flask Application": "flask", # تم تغيير الاسم المعروض
    "Django Application": "django", # تم تغيير الاسم المعروض
}
