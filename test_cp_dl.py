import os
import sys
sys.path.append(os.path.abspath(r"C:\Users\BHAUSAHEB\.gemini\antigravity\scratch\clean-leach-bot"))
from extractors.classplus_api import ClassplusClient
import yt_dlp

org_code = "dqxkl" # Science Magnet
phone = "8624922940"
# Wait, I don't have the OTP to login!
# I can only use the existing token the user provided.
# Let me extract the video directly from the API using the existing token, maybe it's still valid for API calls!

token = "eyJhbGciOiJIUzM4NCIsInR5cCI6IkpXVCJ9.eyJpZCI6MTU0Njc1ODkwLCJvcmdJZCI6NTAxMywidHlwZSI6MSwibW9iaWxlIjoiOTE4NjI0OTIyOTQwIiwibmFtZSI6IkFycGl0IEFycGl0IiwiZW1haWwiOiJhcnBpdHBhdGlsNDY2QGdtYWlsLmNvbSIsImlzSW50ZXJuYXRpb25hbCI6MCwiZGVmYXVsdExhbmd1YWdlIjoiRU4iLCJjb3VudHJ5Q29kZSI6IklOIiwiY291bnRyeUlTTyI6IjkxIiwidGltZXpvbmUiOiJHTVQrNTozMCIsImlzRGl5Ijp0cnVlLCJvcmdDb2RlIjoiZHF4a2wiLCJpc0RpeVN1YmFkbWluIjowLCJmaW5nZXJwcmludElkIjoiMDk3N2QxNzIwZDU5YWEzMmRkOWU2ODA5YzVlNjEzOGRmYjM5ZjBiMDYyMTc3NjIxYTNkODAwMjQwMDY4ZWM4ZSIsImlhdCI6MTc4MDkzMjM5NCwiZXhwIjoxNzgxNTM3MTk0fQ.OldLy51QjElqLbRx-qt3_kw05Jwavxcz2zHayMgkDdLE56Uuoke8jRNZQ3Ul2t_e"

client = ClassplusClient(org_code)
client.headers["x-access-token"] = token
client.headers["device-id"] = "0977d1720d59aa32dd9e6809c5e6138dfb39f0b062177621a3d800240068ec8e"
client.headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"

courses = client.fetch_courses()
print(f"Courses response: {courses}")
if not courses:
    print("Token expired for API calls too!")
    sys.exit(1)

course_id = courses[0]['id']
print(f"Found course: {course_id}")

folders = client.fetch_folders(course_id, "-1")
if folders:
    folder_id = folders[0]['id']
    items = client.fetch_folders(course_id, folder_id)
    video_url = None
    for i in items:
        if str(i.get('contentType')) == "1":
            video_url = i.get('url')
            break
    
    if video_url:
        print(f"Found video URL: {video_url}")
        h = {
            'User-Agent': client.headers["User-Agent"],
            'Referer': 'https://web.classplusapp.com/',
            'Origin': 'https://web.classplusapp.com/',
            'device-id': client.headers["device-id"],
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
                code = ydl.download([video_url])
                print(f"YT-DLP returned: {code}")
        except Exception as e:
            print(f"YT-DLP Exception: {e}")
    else:
        print("No video found in first folder")
