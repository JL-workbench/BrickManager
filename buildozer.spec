[app]
title = BrickManager
package.name = brickmanager
package.domain = com.jlworkbench
source.dir = .
source.include_exts = py,png,jpg,jpeg,json,kv
source.exclude_dirs = .git,.github,.venv,.pytest_cache,tests,build,bin
version = 0.9
requirements = python3==3.10.11,kivy,numpy,requests,opencv
orientation = landscape
fullscreen = 0

# The bundled LEGO colour catalogue is read-only; config.py places runtime
# data in Android's app-specific writable storage.
android.permissions = CAMERA,INTERNET
android.api = 33
android.minapi = 24
android.ndk = 25b
android.archs = arm64-v8a
android.accept_sdk_license = True
p4a.branch = master

[buildozer]
log_level = 2
warn_on_root = 1
