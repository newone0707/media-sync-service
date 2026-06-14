import sys
import os
import urllib.request
import json
from curl_cffi import requests as cffi_requests
sys.path.append(os.path.abspath(r"C:\Users\BHAUSAHEB\.gemini\antigravity\scratch\clean-leach-bot"))
from extractors.api_client import AppxClient

base_url = "https://sciencemagnetapi.classx.co.in"
appx = AppxClient(base_url)
login_resp = appx.login("8617350151", "Dark@9332646241")

if not login_resp.get('success'):
    print("Login failed")
    sys.exit(1)

headers = {
    'User-Agent': 'Mozilla/5.0',
    'appx-version': '3',
    'client-service': 'Appx',
    'auth-key': 'appxapi',
    'device_type': 'WEB',
    'Authorization': appx.token,
    'token': appx.token,
    'User-ID': appx.user_id
}

c_id = "95"
all_items = []
def fetch(pid):
    url = f"{base_url}/get/folder_contentsv2?course_id={c_id}&parent_id={pid}&folder_wise_course=1&userid={appx.user_id}"
    try:
        req = urllib.request.Request(url, headers=headers)
        res = urllib.request.urlopen(req)
        items = json.loads(res.read()).get('data', [])
        all_items.extend(items)
        for i in items:
            if str(i.get('is_folder')) == "1" or str(i.get('resource_type')) in ["2", "0"] or str(i.get('material_type')).upper() == "FOLDER":
                fetch(i['id'])
    except Exception as e:
        print(e)

fetch("-1")

video_url = None
for item in all_items:
    if str(item.get('is_folder')) == "0":
        print(f"File: {item.get('title')}, Resource Type: {item.get('resource_type')}, URL: {item.get('url_1') or item.get('url_2')}")
        if "mkv" in str(item.get('url_1')) or "mkv" in str(item.get('url_2')):
            video_url = item.get('url_1') or item.get('url_2')
        elif str(item.get('resource_type')) == "1":
            video_url = item.get('url_1') or item.get('url_2')

if video_url is None and len(all_items) > 0:
    print("Could not find video, trying the first file URL.")
    for item in all_items:
        if str(item.get('is_folder')) == "0":
            video_url = item.get('url_1') or item.get('url_2')
            if video_url:
                break

if not video_url:
    print("No video found in root folder, try another course or recurse")
    sys.exit(1)

print(f"Found video URL: {video_url}")

h = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': base_url,
    'Origin': base_url
}

print("Downloading with curl_cffi...")
try:
    r = cffi_requests.get(video_url, stream=True, impersonate='chrome', headers=h)
    print(f"Status: {r.status_code}")
    r.raise_for_status()
    print("Success! Appx download works.")
except Exception as e:
    print(f"Download Failed: {e}")
