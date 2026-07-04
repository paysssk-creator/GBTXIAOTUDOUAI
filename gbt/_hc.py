import requests, json
r = requests.get("http://127.0.0.1:8765/api/health")
d = r.json()
print("Status:", d["status"])
print("Code:", r.status_code)
for k, v in d["checks"].items():
    if isinstance(v, dict):
        print(f"  {k}: {v['status']}")
    else:
        print(f"  {k}: {v}")
