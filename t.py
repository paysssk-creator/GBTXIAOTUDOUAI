import urllib.request
try:
    r = urllib.request.urlopen('http://127.0.0.1:8766/favicon.ico')
    print(f'Favicon: {r.status} | Type: {r.headers.get("Content-Type")} | Size: {len(r.read())} bytes')
except Exception as e:
    print(f'Favicon FAIL: {e}')
try:
    r = urllib.request.urlopen('http://127.0.0.1:8766/')
    print(f'Home: {r.status} | Size: {len(r.read())} bytes')
except Exception as e:
    print(f'Home FAIL: {e}')