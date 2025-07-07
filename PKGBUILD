# Maintainer: Your Name <your.email@example.com>
pkgname=hel-web-server
pkgver=1.0.0 # يمكنك تحديث هذا الإصدار بناءً على إصداراتك
pkgrel=1
pkgdesc="A simple web server utility for Helwan Linux, supporting various server types like Django and Flask."
arch=('any') # يمكن تشغيله على أي معمارية تدعم Python
url="https://github.com/helwan-linux/helwan-server" # يرجى تحديث هذا الرابط إذا كان مختلفًا
license=('GPL') # أو أي ترخيص آخر تستخدمه
depends=('python' 'python-pyqt5' 'python-setuptools' 'desktop-file-utils') # أضفنا python-setuptools و desktop-file-utils

# إذا كان لديك ملف مضغوط للمشروع، ضع اسمه هنا.
# إذا كان المستودع على GitHub يعمل، يمكنك استخدام:
# source=("${pkgname}-${pkgver}.tar.gz::https://github.com/helwan-linux/helwan-server/archive/v${pkgver}.tar.gz")
# sha256sums=('SKIP') # أو قم بتوليدها بعد تنزيل المصدر

# بما أننا لا نملك رابط GitHub يعمل حالياً، سنفترض أن الملف سيتم توفيره يدوياً
# أو يمكنك استخدام هذا إذا كان المشروع متاحاً كملف مضغوط محلياً:
source=("${pkgname}-${pkgver}.tar.gz") # مثال: hel-web-server-1.0.0.tar.gz
sha256sums=('SKIP') # يجب استبدال 'SKIP' بالمجموع الاختباري الفعلي لملف المصدر بعد تنزيله

build() {
  cd "${srcdir}/${pkgname}-${pkgver}" # أو "${srcdir}/${pkgname}" إذا كان المجلد لا يحتوي على رقم الإصدار
  # لا توجد خطوة بناء معقدة لبرامج Python البسيطة
  # يمكن أن تكون هذه الخطوة فارغة أو تحتوي على أوامر إعداد إذا لزم الأمر
}

package() {
  # قم بإنشاء أدلة التثبيت
  install -d "${pkgdir}/usr/bin/"
  install -d "${pkgdir}/usr/share/${pkgname}/"
  install -d "${pkgdir}/usr/share/applications/" # لملف .desktop

  # نسخ ملفات المشروع إلى /usr/share/hel-web-server/
  # تأكد من أن هذا المسار يتطابق مع المجلد الذي يحتوي على hel_web_server.py
  # بناءً على هيكل الملفات الذي قدمته (hel_web_server.py في الجذر)
  cp -r "${srcdir}/${pkgname}-${pkgver}/." "${pkgdir}/usr/share/${pkgname}/"

  # إنشاء سكريبت تشغيل في /usr/bin/
  # هذا يسمح للمستخدم بتشغيل البرنامج بكتابة 'hel-web-server' في الطرفية
  cat << EOF > "${pkgdir}/usr/bin/${pkgname}"
#!/bin/bash
python "/usr/share/${pkgname}/hel_web_server.py" "\$@"
EOF

  chmod +x "${pkgdir}/usr/bin/${pkgname}" # جعل السكريبت قابلاً للتنفيذ

  # إنشاء ملف .desktop لتكامل سطح المكتب
  # إذا كان لديك ملف Hel-Web-Server.desktop موجود بالفعل في المصدر،
  # يمكنك ببساطة نسخه بدلاً من إنشائه هنا:
  # install -m644 "${srcdir}/${pkgname}-${pkgver}/Hel-Web-Server.desktop" "${pkgdir}/usr/share/applications/"
  
  # إذا لم يكن موجوداً في المصدر، قم بإنشائه:
  cat << EOF > "${pkgdir}/usr/share/applications/${pkgname}.desktop"
[Desktop Entry]
Name=Hel-Web-Server
Comment=A simple web server utility for Helwan Linux
Exec=/usr/bin/${pkgname}
Icon=${pkgname} # يمكن أن يكون مساراً كاملاً لأيقونة إذا كانت موجودة في /usr/share/icons
Terminal=false
Type=Application
Categories=Development;Utility;
EOF

  # تحديث قاعدة بيانات ملفات سطح المكتب
  # هذا الأمر يتم تشغيله بعد التثبيت لضمان ظهور التطبيق في قوائم التطبيقات
  # وقد لا يكون ضرورياً داخل package() ولكنه ممارسة جيدة
  # يمكن أيضاً تشغيله كـ post-install hook
  # ولكن لضمان التثبيت الصحيح، سنضعه هنا
  update-desktop-database -q || true
}
