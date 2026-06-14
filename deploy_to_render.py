import urllib.request
import json
import sys
import time

api_key = "rnd_Cehgb9tEsJqyO1IkWOE4cpy5e2zz"
repo_url = "https://github.com/newone0707/cloud-media-service"

def make_request(url, method="GET", data=None):
    req = urllib.request.Request(url, method=method)
    req.add_header("Authorization", f"Bearer {api_key}")
    req.add_header("Accept", "application/json")
    if data:
        req.add_header("Content-Type", "application/json")
        req.data = json.dumps(data).encode("utf-8")
    
    try:
        res = urllib.request.urlopen(req)
        return json.loads(res.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"HTTP Error: {e.code} {e.reason}")
        print(e.read().decode("utf-8"))
        sys.exit(1)

print("Fetching Render owner ID...")
owners = make_request("https://api.render.com/v1/owners")
owner_id = owners[0]['owner']['id']
print(f"Owner ID: {owner_id}")

print("Creating service...")
service_data = {
    "type": "web_service",
    "name": "cloud-media-service",
    "plan": "free",
    "ownerId": owner_id,
    "repo": repo_url,
    "autoDeploy": "yes",
    "branch": "main",
    "env": "python",
    "envVars": [
        {"key": "PYTHON_VERSION", "value": "3.10.11"}
    ],
    "serviceDetails": {
        "env": "python",
        "envSpecificDetails": {
            "buildCommand": "pip install -r requirements.txt",
            "startCommand": "python bot.py"
        }
    }
}

service = make_request("https://api.render.com/v1/services", method="POST", data=service_data)
print("Service created successfully!")
print(f"Service ID: {service['id']}")
print(f"Service Name: {service['service']['name']}")
print(f"Dashboard URL: {service['service']['dashboardUrl']}")
