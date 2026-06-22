import os, re
BASE = r"C:\Users\ADMIN\GBTXIAOTUDOUAI"
path = os.path.join(BASE, "native_app.py")
with open(path, "r", encoding="utf-8") as f:
    content = f.read()
# Fix all split strings: line ending with + "\n followed by ") on next line
content = re.sub(r' \+ "\n\n"\)', r' + "\\n")', content)
with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("Fixed all split strings in native_app.py")
