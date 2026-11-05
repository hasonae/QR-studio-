[app]

title = QR Studio
package.name = qrstudio
package.domain = app.qrstudio
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,txt,md
version = 1.0.0
# Let python-for-android select its matching Python and hostpython versions.
# Pinning this to 3.11.5 conflicts with p4a's hostpython3 3.14.2.
requirements = python3,kivy,qrcode,pillow
# Use the stable python-for-android branch rather than develop.
p4a.branch = master
orientation = portrait
fullscreen = 0

# Android packaging
android.api = 35
android.minapi = 24
android.ndk = 25b
android.archs = arm64-v8a, armeabi-v7a
android.accept_sdk_license = True
android.allow_backup = False

# This app creates QR images locally and does not need internet, camera,
# contacts, location, or broad storage permissions.

# Replace with your own 512x512 PNG before release if desired.
icon.filename = app_icon.png

[buildozer]
log_level = 2
warn_on_root = 1
