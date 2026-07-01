"""Quick test for LinkGen + 3D Globe"""
import sys; sys.path.insert(0,'.')
from gbt.linkgen import generate, get_services, validate_url

print('=== URL Validation ===')
print('Valid https:', validate_url('https://github.com'))
print('Valid http:', validate_url('http://example.com'))
print('Invalid:', validate_url('not-a-url'))

print('\n=== Available Services ===')
for s in get_services():
    print(f'  {s["icon"]} {s["name"]} ({s["id"]}) - {s["region"]}')

print('\n=== Generate Short Link ===')
r = generate('https://github.com/paysssk-creator/GBTXIAOTUDOUAI')
print('Result:', r.get('ok'), '| Short:', r.get('short','N/A'), '| Service:', r.get('service','N/A'), '| TTL:', r.get('ttl_ms','N/A'), 'ms')

from gbt.linkgen_3d import add_link, start_server, status
add_link(r.get('original','https://example.com'), r.get('short',''), r.get('service',''))
print('\n=== 3D Server Status (before start) ===')
print(status())

print('\n=== Start 3D Server ===')
srv = start_server()
print('Server:', srv)
print('Status after start:', status())
