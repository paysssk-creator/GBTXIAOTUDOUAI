import urllib.request
try:
    data = urllib.request.urlopen(
        "https://raw.githubusercontent.com/paysssk-creator/GBTXIAOTUDOUAI/main/gbt/capabilities.py",
        timeout=10
    ).read().decode("utf-8")
    idx = data.index("_handler_screen_ocr")
    print(data[idx:][:3000])
except (urllib.error.URLError, ValueError, UnicodeDecodeError, OSError) as e:
    print(f"fetch failed: {e}")
