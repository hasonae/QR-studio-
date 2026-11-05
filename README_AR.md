# QR Studio — تطبيق QR Maker بلغة Python وKivy

تطبيق لتوليد رموز QR محليًا على الهاتف، مع واجهة داكنة، تخصيص الألوان، معاينة، مكتبة محلية، وتصدير PNG.

## الميزات الموجودة

- إنشاء QR للروابط والنصوص وشبكات Wi‑Fi وجهات الاتصال vCard والبريد الإلكتروني وأرقام الهاتف ورسائل SMS.
- تطبيع روابط المواقع بإضافة `https://` عند الحاجة.
- التحقق من الحقول الأساسية قبل الإنشاء.
- خمسة ألوان أمامية وثلاثة ألوان خلفية مع تباين مناسب.
- أربعة مستويات لتصحيح الأخطاء.
- معاينة فورية وتصدير PNG بدقة 1024×1024.
- حفظ نسخة في مكتبة التطبيق وسجل JSON محلي.
- على Android 10 وما بعده: محاولة حفظ الصورة مباشرة في `Pictures/QR Studio` عبر MediaStore دون طلب إذن تخزين شامل.
- فتح العناصر المحفوظة واستعادة حقولها الأساسية، أو حذف عنصر أو مسح المكتبة.
- مشاركة صورة PNG عبر قائمة المشاركة في Android بعد حفظها إلى معرض الصور؛ وعند تعذر ذلك ينسخ التطبيق محتوى QR إلى الحافظة كبديل.
- لا يحتاج إنشاء QR إلى الإنترنت أو الكاميرا أو خادم خارجي.

## هيكل المشروع

```text
qr_studio_android/
├── main.py
├── buildozer.spec
└── README_AR.md
```

## التشغيل على الكمبيوتر للاختبار

يتطلب Python 3.10 أو أحدث، ثم:

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install kivy qrcode pillow
python main.py
```

## بناء APK على Windows 10/11 باستخدام WSL2

Buildozer وpython-for-android يعملان من بيئة Linux؛ على Windows استخدم WSL2 مع Ubuntu، وضع المشروع داخل نظام ملفات Linux مثل `~/projects/qr_studio_android` وليس داخل `/mnt/c` لتقليل مشاكل البناء.

داخل Ubuntu/WSL2:

```bash
sudo apt update
sudo apt install -y python3-pip python3-venv git zip unzip openjdk-17-jdk \
  autoconf libtool pkg-config zlib1g-dev libncurses5-dev libncursesw5-dev \
  libtinfo6 cmake libffi-dev libssl-dev

cd ~/projects/qr_studio_android
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install buildozer cython==0.29.36
buildozer android debug
```

عند اكتمال البناء سيكون ملف APK داخل مجلد `bin/`. انقله إلى الهاتف وثبّته مع السماح بالتثبيت من هذا المصدر عند طلب Android ذلك.

لتثبيت التطبيق وتشغيله عبر USB بعد تفعيل USB debugging:

```bash
buildozer android debug deploy run
```

## ملاحظات Android مهمة

1. أول عملية بناء تنزّل Android SDK/NDK ومكونات البناء، ولذلك تحتاج اتصالًا بالإنترنت ومساحة تخزين كافية.
2. يلزم بناء APK على Linux أو macOS؛ على Windows استخدم WSL2. لا يمكن تحويل ملف Python إلى APK بمجرد تشغيله داخل Pydroid.
3. لا يحتوي الإصدار الحالي على ماسح بالكاميرا. أُبقيت هذه الوظيفة خارج النطاق الأول لتجنب دمج مكتبات native إضافية قبل التأكد من استقرار النسخة الأساسية.
4. حفظ الصور داخل مجلد التطبيق يعمل كخيار احتياطي. أما الحفظ المباشر إلى معرض الصور فيستخدم Android MediaStore، ويُجرّب تلقائيًا عند التشغيل على Android.
5. قبل النشر على Google Play، راجع متطلبات Target API السارية وقت النشر، وقد تحتاج إلى تحديث `android.api` بحسب إصدار python-for-android/Buildozer المتاح لديك.
6. إعدادات التوقيع وإصدار Release ليست مضمنة؛ ملف debug مخصص للاختبار والتثبيت الشخصي.

## تخصيص الهوية

- عدّل `title` و`package.name` و`package.domain` في `buildozer.spec` قبل أول إصدار.
- استبدل `app_icon.png` بأيقونة 512×512 خاصة بك إن رغبت.
- الألوان والخطوط والأقسام الرئيسية معرفة في بداية `main.py`.
