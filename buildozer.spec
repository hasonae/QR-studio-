[app]

title = QR Studio
package.name = qrstudio
package.domain = app.qrstudio
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,txt,md
version = 1.0.0
requirements = python3,kivy,qrcode,pillow
p4a.branch = master
orientation = portrait
fullscreen = 0

android.api = 35
android.minapi = 24
android.ndk = 25b
android.archs = arm64-v8a, armeabi-v7a
android.accept_sdk_license = True
android.allow_backup = False

icon.filename = app_icon.png

[buildozer]
log_level = 2
warn_on_root = 1
