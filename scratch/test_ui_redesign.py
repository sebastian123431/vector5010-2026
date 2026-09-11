import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vector5010.settings')
import django
django.setup()

from django.test import Client

client = Client()

print("--- Test 1: GET /redes/ (Main Workstation View) ---")
res = client.get('/redes/')
assert res.status_code == 200, f"Expected 200, got {res.status_code}"
content = res.content.decode('utf-8')

assert "VECTOR 2026" in content, "VECTOR 2026 not found in HTML"
assert "Núcleo Soberano" in content, "Núcleo Soberano not found in HTML"
assert "Cockpit Dividido" in content, "Cockpit Dividido not found in HTML"
assert "sidebar-session-list" in content, "sidebar-session-list not found in HTML"
assert "btn-new-conversation" in content, "btn-new-conversation not found in HTML"

# Verify that legacy hardcoded strings are GONE
legacy_terms = ["316 neuronas", "red social", "vínculos", "amigos", "familia", "show-create-person", "show-person-list"]
for term in legacy_terms:
    assert term not in content.lower(), f"Found legacy term in HTML: {term}"

print("[OK] GET /redes/ passed! Zero legacy terms found.")

print("--- Test 2: GET /redes/neuronal/data/ ---")
res_data = client.get('/redes/neuronal/data/')
assert res_data.status_code == 200, f"Expected 200, got {res_data.status_code}"
json_data = res_data.json()
assert 'nodes' in json_data and 'edges' in json_data
print(f"[OK] Neuronal data OK! {len(json_data['nodes'])} nodes, {len(json_data['edges'])} edges.")

print("--- Test 3: GET /api/chat/sesiones/ ---")
res_ses = client.get('/api/chat/sesiones/?user_name=Sebastian')
assert res_ses.status_code == 200
print(f"[OK] Chat sessions endpoint OK! {len(res_ses.json().get('sesiones', []))} sesiones.")

print("--- Test 4: GET /api/sentinel/status/ ---")
res_sen = client.get('/api/sentinel/status/')
assert res_sen.status_code == 200
print(f"[OK] Sentinel status OK! CPU: {res_sen.json().get('cpu')}%, RAM: {res_sen.json().get('ram')}%")

print("--- Test 5: GET /redes/home/ ---")
res_home = client.get('/redes/home/')
assert res_home.status_code == 200
home_content = res_home.content.decode('utf-8')
assert "Personas y Conexiones" not in home_content
assert "Nueva Persona" not in home_content
assert "Visión Computacional" in home_content
print("[OK] Home view OK! Modern dark landing without legacy person links.")

print("\nALL TESTS PASSED SUCCESSFULLY!")
