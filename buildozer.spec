[app]
title = BrickManager
package.name = brickmanager
package.domain = com.jlworkbench
source.dir = .
source.include_exts = py,png,jpg,jpeg,json,kv
source.exclude_dirs = .git,.github,.venv,.pytest_cache,tests,build,bin
version = 0.9
# Python-Version bewusst festlegen.
# python3 und hostpython3 müssen identisch sein.
requirements = python3==3.10.11,hostpython3==3.10.11,kivy,numpy,requests,opencv
orientation = landscape
fullscreen = 0

android.permissions = CAMERA,INTERNET
android.api = 33
android.minapi = 24
android.ndk = 25b
android.archs = arm64-v8a
# Python-for-Android auf die letzte stabile Version
# mit Python 3.10 festlegen.
p4a.branch = master
p4a.commit = e155baf9

[buildozer]
log_level = 2
warn_on_root = 1
