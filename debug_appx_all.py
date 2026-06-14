import requests

urls = [
    "https://static-trans-v1.appx.co.in/videos/vishalkhodifad-data/526248-1706260805/encrypted-401185/360p/encrypted.mp4?URLPrefix=aHR0cHM6Ly9zdGF0aWMtdHJhbnMtdjEuYXBweC5jby5pbi92aWRlb3MvdmlzaGFsa2hvZGlmYWQtZGF0YS81MjYyNDgtMTcwNjI2MDgwNS9lbmNyeXB0ZWQtNDAxMTg1LzM2MHAvZW5jcnlwdGVkLm1wNA&Expires=1781367043&KeyName=appx-pdf-keyset&Signature=kC7GdQXeXfP3K5ve5rDqyJ2ZUnC5fRcxi88X6JqIib9WplmuS6cxypOPoggoNpIRRMoPqgjmaB0xwPLZrE3ZAQ*RI5we8T5/ZXsZp4kGpNMpw==:ZmVkY2JhOTg3NjU0MzIxMA==",
    "https://static-trans-v1.appx.co.in/videos/vishalkhodifad-data/115807-1727001822/encrypted-45db0e/360p.zip?URLPrefix=aHR0cHM6Ly9zdGF0aWMtdHJhbnMtdjEuYXBweC5jby5pbi92aWRlb3MvdmlzaGFsa2hvZGlmYWQtZGF0YS8xMTU4MDctMTcyNzAwMTgyMi9lbmNyeXB0ZWQtNDVkYjBlLzM2MHAuemlw&Expires=1781370008&KeyName=appx-pdf-keyset&Signature=LLN1MUbBQX0pYIuBhc4VaqhMrMwD22EfMpPSeu5uFb_lhwQdcr2NLFvWYVCouMaBSIqnN-NhQAkP-WUficsbDQ",
    "https://static-db.appx.co.in/paid_course4/2024-09-22-0.06268889197194172.pdf?URLPrefix=aHR0cHM6Ly9zdGF0aWMtZGIuYXBweC5jby5pbi9wYWlkX2NvdXJzZTQvMjAyNC0wOS0yMi0wLjA2MjY4ODg5MTk3MTk0MTcyLnBkZg&Expires=1781370007&KeyName=appx-pdf-keyset&Signature=6fcWzXXTQvFtSoOAAuJ2L27Bp1QICQgzEOz35AQRwi6qhaWbYF18fwWYlztlZyVO9rzertzazVE-vEKxc82zAQ"
]

for u in urls:
    if ":Zm" in u or ":" in u.split("/")[-1]:
        parts = u.rsplit(":", 1)
        if len(parts) == 2 and len(parts[1]) > 10 and "=" in parts[1]:
            u = parts[0]
    
    r = requests.get(u, headers={'User-Agent': 'Mozilla/5.0'})
    print(f"URL: {u}\nStatus: {r.status_code}\n")
