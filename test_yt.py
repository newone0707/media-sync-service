import yt_dlp
import sys

# Use an old URL just to see what error yt-dlp spits out (since user said download failed).
# We just want to see the stdout/stderr of yt-dlp.
url = "https://media-cdn.classplusapp.com/5013/cc/25acc33befa044028c0d116c5fd24cbb-ih/master.m3u8?contentHashId=U2FsdGVkX19YGZ4PanwUEElpZHr%2B8rP1Zh3RZUK2rGw%3D&token=eyJhbGciOiJIUzM4NCIsInR5cCI6IkpXVCJ9.eyJpZCI6MTU0Njc1ODkwLCJvcmdJZCI6NTAxMywidHlwZSI6MSwibW9iaWxlIjoiOTE4NjI0OTIyOTQwIiwibmFtZSI6IkFycGl0IEFycGl0IiwiZW1haWwiOiJhcnBpdHBhdGlsNDY2QGdtYWlsLmNvbSIsImlzSW50ZXJuYXRpb25hbCI6MCwiZGVmYXVsdExhbmd1YWdlIjoiRU4iLCJjb3VudHJ5Q29kZSI6IklOIiwiY291bnRyeUlTTyI6IjkxIiwidGltZXpvbmUiOiJHTVQrNTozMCIsImlzRGl5Ijp0cnVlLCJvcmdDb2RlIjoiZHF4a2wiLCJpc0RpeVN1YmFkbWluIjowLCJmaW5nZXJwcmludElkIjoiMDk3N2QxNzIwZDU5YWEzMmRkOWU2ODA5YzVlNjEzOGRmYjM5ZjBiMDYyMTc3NjIxYTNkODAwMjQwMDY4ZWM4ZSIsImlhdCI6MTc4MDkzMjM5NCwiZXhwIjoxNzgxNTM3MTk0fQ.OldLy51QjElqLbRx-qt3_kw05Jwavxcz2zHayMgkDdLE56Uuoke8jRNZQ3Ul2t_e"
token = url.split("token=")[1].split("&")[0]

h = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Referer': 'https://web.classplusapp.com/',
    'Origin': 'https://web.classplusapp.com/',
    'device-id': '0977d1720d59aa32dd9e6809c5e6138dfb39f0b062177621a3d800240068ec8e',
    'x-access-token': token
}

ydl_opts = {
    'format': 'best',
    'http_headers': h,
    'impersonate': 'chrome',
    'verbose': True
}

try:
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        code = ydl.download([url])
        print(f"YT-DLP return code: {code}")
except Exception as e:
    print(f"YT-DLP Exception: {e}")

from curl_cffi import requests as cffi_requests
try:
    r = cffi_requests.get(url, headers=h, impersonate='chrome')
    print(f"Curl_Cffi status: {r.status_code}")
except Exception as e:
    print(f"Curl_Cffi Error: {e}")
