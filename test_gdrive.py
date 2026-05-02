import requests
import json
import re

folder_id = "14qHKKorZQwzXki3ZxGS9B5plRVOxlcgt"
base_url = f"https://drive.google.com/drive/folders/{folder_id}"
headers = {"User-Agent": "Mozilla/5.0"}
res = requests.get(base_url, headers=headers)
html = res.text
data_match = re.search(r"window\['_DRIVE_ivd'\]\s*=\s*'(.*?)';", html)
if data_match:
    raw_data = data_match.group(1).encode().decode('unicode_escape')
    data = json.loads(raw_data)
    print("Files part:", len(data[0]))
    print("Next token:", data[1])
else:
    print("No ivd found")
