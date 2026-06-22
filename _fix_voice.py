"""Fix _voice_speak to use Python API instead of CLI"""
with open(r"C:\Users\ADMIN\GBTXIAOTUDOUAI\gbt\winctl.py", "r", encoding="utf-8") as f:
    content = f.read()

old = '            import shutil\n            if shutil.which("edge-tts"):'
new = '            import edge_tts as _etts\n            if True:'

if old in content:
    content = content.replace(old, new, 1)
    print("Replaced shutil -> edge_tts import")
else:
    print("NOT FOUND: shutil import")

# Replace CLI subprocess.run with Python API
old2 = '''                subprocess.run([
                    "edge-tts",
                    "--voice", cfg["voice"],
                    "--rate", cfg["rate"],
                    "--pitch", cfg["pitch"],
                    "--text", text,
                    "--write-media", tmp,
                ], capture_output=True, timeout=30, check=True)'''

new2 = '''                async def _gen():
                    c = _etts.Communicate(text, voice=cfg["voice"],
                                          rate=cfg["rate"], pitch=cfg["pitch"])
                    await c.save(tmp)

                asyncio.run(_gen())'''

if old2 in content:
    content = content.replace(old2, new2, 1)
    print("Replaced CLI with Python API")
else:
    print("NOT FOUND: CLI code")

# Fix creationflags
old3 = 'creationflags=subprocess.CREATE_NO_WINDOW'
new3 = 'creationflags=0x08000000'
if old3 in content:
    content = content.replace(old3, new3, 1)
    print("Fixed creationflags")

with open(r"C:\Users\ADMIN\GBTXIAOTUDOUAI\gbt\winctl.py", "w", encoding="utf-8") as f:
    f.write(content)

print("DONE - voice method updated")
