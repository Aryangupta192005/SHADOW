"""
diagnose.py — run this once from your SHADOW folder (venv activated) to see
exactly why open_application/smart_open can't find WhatsApp/Telegram.

    python diagnose.py

Delete this file afterward — it's just a debugging tool, not part of SHADOW.
"""
import os
import subprocess

import tools.applications as app

print("1. Is this the UPDATED applications.py? (should be True)")
print("   has _resolve_uwp_app:", hasattr(app, "_resolve_uwp_app"))
print()

print("2. PATH check (shutil.which):")
print("   whatsapp:", app.shutil.which("whatsapp"), "| WhatsApp.exe:", app.shutil.which("WhatsApp.exe"))
print("   telegram:", app.shutil.which("telegram"), "| Telegram.exe:", app.shutil.which("Telegram.exe"))
print()

print("3. Start Menu directories being searched:")
for d in app._START_MENU_DIRS:
    print("  ", d, "-> exists:", os.path.isdir(d))
print()

print("4. Extra install-directory search paths:")
for d in app._EXTRA_SEARCH_DIRS:
    print("  ", d, "-> exists:", os.path.isdir(d))
print()

print("5. Searching Start Menu folders for any .lnk containing 'whatsapp' or 'telegram':")
found_any = False
for base in app._START_MENU_DIRS:
    if not os.path.isdir(base):
        continue
    for root, dirs, files in os.walk(base):
        for f in files:
            if "whatsapp" in f.lower() or "telegram" in f.lower():
                print("   FOUND:", os.path.join(root, f))
                found_any = True
if not found_any:
    print("   (none found)")
print()

if hasattr(app, "_resolve_uwp_app"):
    print("6. Direct UWP/Microsoft Store package lookup for 'whatsapp':")
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "Get-AppxPackage | Where-Object { $_.Name -like '*whatsapp*' } | Select-Object Name, PackageFamilyName"],
        capture_output=True, text=True, timeout=15,
    )
    print("   stdout:", repr(result.stdout))
    print("   stderr:", repr(result.stderr))
else:
    print("6. SKIPPED — this is the OLD applications.py, the UWP fix isn't in it.")
    print("   You need to re-copy the full applications.py I gave you.")