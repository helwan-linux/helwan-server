# ملف: app.py
from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return '<h1>Flask Application Works! ✅</h1><p>This is served by the Flask development server.</p>'

if __name__ == '__main__':
    # ملاحظة: البرنامج هو من يشغل الدالة run، لكن هذا الكود ضروري لتعريف التطبيق.
    app.run(debug=True)