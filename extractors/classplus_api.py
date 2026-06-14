import json
from curl_cffi import requests
import concurrent.futures

class ClassplusClient:
    def __init__(self, org_code):
        self.base_url = "https://api.classplusapp.com"
        self.org_code = org_code
        self.total_videos = 0
        self.total_pdfs = 0
        self.session = requests.Session(impersonate="chrome110")
        self.token = None
        self.user_id = None
        
        self.headers = {
            "api-version": "29",
            "user-agent": "Mobile-Android",
            "app-version": "1.4.65.3",
            "device-id": "39F093FF35F201D9",
            "Content-Type": "application/json",
            "x-access-token": ""
        }

    def generate_otp(self, mobile, country_ext="91"):
        url = f"{self.base_url}/v2/otp/generate"
        payload = {
            "orgCode": self.org_code,
            "mobile": mobile,
            "countryExt": country_ext
        }
        try:
            res = self.session.post(url, json=payload, headers=self.headers)
            return res.json()
        except Exception as e:
            return {"success": False, "message": str(e)}

    def verify_otp(self, mobile, otp, country_ext="91"):
        url = f"{self.base_url}/v2/users/verify"
        payload = {
            "orgCode": self.org_code,
            "mobile": mobile,
            "otp": otp,
            "countryExt": country_ext
        }
        try:
            res = self.session.post(url, json=payload, headers=self.headers)
            resp_json = res.json()
            if resp_json.get("status") == "success" or resp_json.get("data"):
                data = resp_json.get("data", {})
                self.token = data.get("token")
                self.user_id = data.get("user", {}).get("id")
                self.headers["x-access-token"] = self.token
                return {"success": True, "data": data}
            return {"success": False, "error": resp_json.get("message", "Invalid OTP")}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def fetch_courses(self):
        if not self.token:
            return {"success": False, "error": "Not authenticated"}
            
        url = f"{self.base_url}/v2/courses"
        try:
            res = self.session.get(url, headers=self.headers)
            try:
                resp = res.json()
                return {"success": True, "data": resp}
            except:
                return {"success": False, "error": f"API returned non-JSON: {res.text}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_signed_url(self, file_url, content_id, course_id, folder_id):
        if not file_url:
            return ""
        if content_id and any(x in file_url for x in ["classplusapp.com", "tencdn.classplusapp", "videos.classplusapp", "media-cdn"]):
            f_id = folder_id if folder_id else 0
            return f"{file_url}?contentId={content_id}&courseId={course_id}&folderId={f_id}&token={self.token}"
        return file_url

    def extract_links(self, course_id):
        links = []
        
        def traverse(folder_id, path):
            url = f"{self.base_url}/v2/course/content/get?courseId={course_id}"
            if folder_id:
                url += f"&folderId={folder_id}"
                
            try:
                res = self.session.get(url, headers=self.headers).json()
                items = res.get("data", {}).get("courseContent", [])
                
                for item in items:
                    c_type = item.get("contentType")
                    name = item.get("name", "Unknown").replace(":", "-").strip()
                    
                    if c_type == 1: # Folder
                        traverse(item["id"], path + f"{name}/")
                    else: # File/Video
                        file_url = item.get("url")
                        if file_url:
                            if c_type == 2:
                                self.total_videos += 1
                                content_id = item.get("id")
                                file_url = self.get_signed_url(file_url, content_id, course_id, folder_id)
                            elif c_type == 3:
                                self.total_pdfs += 1
                            links.append(f"{path}{name}: {file_url}")
            except Exception as e:
                print(f"Error traversing folder {folder_id}: {e}")

        traverse(None, "")
        
        # Fetch Live Videos
        try:
            live_url = f"{self.base_url}/v2/course/live/list/videos?type=2&entityId={course_id}&limit=9999&offset=0"
            live_res = self.session.get(live_url, headers=self.headers).json()
            live_items = live_res.get("data", {}).get("list", [])
            for item in live_items:
                name = item.get("name", "Live Video").replace(":", "-").strip()
                video_url = item.get("url")
                if video_url:
                    self.total_videos += 1
                    content_id = item.get("id")
                    signed_url = self.get_signed_url(video_url, content_id, course_id, 0)
                    links.append(f"Live - {name}: {signed_url}")
        except Exception as e:
            print(f"Error fetching live videos: {e}")
            
        return links
