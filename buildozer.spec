[app]
title = BrickManager
package.name = brickmanager
package.domain = com.jlworkbench

source.dir = .
source.include_exts = py,png,jpg,jpeg,json,kv
source.exclude_dirs = .git,.github,.venv,.pytest_cache,tests,build,bin

version = 0.9

requirements = python3==3.10.11,kivy,numpy,requests
p4a_recipes = opencv

orientation = landscape
fullscreen = 0

android.permissions = CAMERA,INTERNET
android.api = 33
android.sdk = 34
android.ndk = 26.1.10909125
android.accept_sdk_license = True
android.archs = arm64-v8a

p4a.branch = master
p4a.commit = e155baf9

[buildozer]
log_level = 2
warn_on_root = 1