import asyncio
import json
import re
import requests
from urllib.parse import urlparse, unquote
from urllib.parse import urlparse, unquote

class SpayeeClient:
    def __init__(self, base_url, email, password):
        self.base_url = base_url
        self.email = email
        self.password = password
        
        parsed_url = urlparse(base_url)
        self.domain_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        self.domain_host = parsed_url.netloc
        
        self.total_videos = 0
        self.total_pdfs = 0
        self.courses = []
        self.raw_links = []
        
        # Detect auth mode
        if self.email and self.email.lower() == "token":
            self.token = self.password
            self.session_id = None
        elif self.email and self.email.lower() == "cookie":
            # cookie mode: password contains "SESSIONID=xxx;c_ujwt=yyy"
            self.token = None
            self.session_id = None
            self._parse_cookies(self.password)
        else:
            self.token = None
            self.session_id = None
    
    def _parse_cookies(self, cookie_str):
        """Parse cookie string like SESSIONID=xxx;c_ujwt=yyy"""
        self.cookie_dict = {}
        for part in cookie_str.split(";"):
            part = part.strip()
            if "=" in part:
                k, v = part.split("=", 1)
                self.cookie_dict[k.strip()] = v.strip()
        self.session_id = self.cookie_dict.get("SESSIONID")
        self.token = self.cookie_dict.get("c_ujwt") or self.cookie_dict.get("jwt")
        
    def _login_api(self):
        """Pure backend requests login to bypass Playwright and Cloudflare blocks"""
        if not self.email or not self.password or self.email.lower() in ['token', 'cookie']:
            return {"success": False, "error": "Invalid credentials format"}
            
        try:
            session = requests.Session()
            url = f"{self.domain_url}/s/authenticate"
            data = {
                'email': self.email,
                'password': self.password,
                'age': '',
                'url': '/s/authenticate'
            }
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            r = session.post(url, data=data, headers=headers, allow_redirects=False, timeout=15)
            
            cookies = session.cookies.get_dict()
            if 'c_ujwt' in cookies:
                self.token = cookies['c_ujwt']
                self.session_id = cookies.get('SESSIONID')
                return {"success": True}
            elif r.status_code == 200:
                return {"success": False, "error": "Invalid email or password"}
            else:
                return {"success": False, "error": f"Login returned status {r.status_code}"}
        except Exception as e:
            return {"success": False, "error": f"Login request failed: {e}"}

    async def fetch_courses(self):
        try:
            if not getattr(self, 'session_id', None) or not getattr(self, 'token', None):
                login_res = self._login_api()
                if not login_res.get("success"):
                    return {"success": False, "error": login_res.get("error", "Login failed")}
            
            api_result = await self._fetch_courses_api()
            if api_result.get("success"):
                return api_result
            return {"success": False, "error": "No courses found"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _fetch_courses_from_store(self):
        """Fetch courses from the public store page using requests (fast, no browser needed)"""
        try:
            session = requests.Session()
            session.headers.update({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            })
            
            if self.token:
                session.cookies.set("c_ujwt", self.token, domain=self.domain_host, path="/")
                session.cookies.set("jwt", self.token, domain=self.domain_host, path="/")
            if self.session_id:
                session.cookies.set("SESSIONID", self.session_id, domain=self.domain_host, path="/")
            
            r = session.get(f"{self.domain_url}/s/store", timeout=15)
            
            if r.status_code != 200:
                return []
            
            courses = []
            seen = set()
            
            matches = re.findall(r'href="(https?://[^"]*?/courses/([^"]+)-([a-f0-9]{24}))"', r.text)
            for full_url, title_slug, course_id in matches:
                if course_id not in seen:
                    seen.add(course_id)
                    title = unquote(title_slug).replace('-', ' ')
                    courses.append({"id": full_url, "title": title})
            
            cat_matches = re.findall(r'href="(https?://[^"]*?/s/store/courses/([^"]+))"', r.text)
            for full_url, cat_name in cat_matches:
                cat_name_decoded = unquote(cat_name)
                if cat_name_decoded not in seen and not cat_name_decoded.startswith('<'):
                    seen.add(cat_name_decoded)
                    try:
                        cr = session.get(full_url, timeout=10)
                        cat_courses = re.findall(r'href="(https?://[^"]*?/courses/([^"]+)-([a-f0-9]{24}))"', cr.text)
                        for curl, ctitle, cid in cat_courses:
                            if cid not in seen:
                                seen.add(cid)
                                courses.append({"id": curl, "title": unquote(ctitle).replace('-', ' ')})
                    except:
                        pass
            
            content_matches = re.findall(r'/s/store/content/([a-f0-9]{24})', r.text)
            for cid in content_matches:
                if cid not in seen:
                    seen.add(cid)
                    courses.append({"id": f"{self.domain_url}/s/store/content/{cid}", "title": f"Course {cid[:8]}"})
            
            return courses
            
        except Exception as e:
            print(f"Store fetch error: {e}")
            return []

    async def _fetch_courses_api(self):
        """Fetch courses using the internal API directly if cookies are present"""
        import aiohttp
        url = f"{self.domain_url}/s/mycourses/get?skip=0&limit=100&queryData=%7B%7D&isVerticalFilters=true&categoryLevel=0&archived=false"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json"
        }
        
        # Build cookies
        cookies = {}
        if self.token:
            cookies["jwt"] = self.token
            cookies["c_ujwt"] = self.token
        if self.session_id:
            cookies["SESSIONID"] = self.session_id
            
        try:
            async with aiohttp.ClientSession(cookies=cookies) as session:
                async with session.get(url, headers=headers) as response:
                    if response.status != 200:
                        return {"success": False, "error": f"API returned {response.status}. Session expired or invalid cookies."}
                    data = await response.json()
                    
                    if not isinstance(data, dict) or "data" not in data or "data" not in data.get("data", {}):
                        return {"success": False, "error": f"Unexpected API response format: {str(data)[:100]}"}
                        
                    unique = []
                    for item in data["data"]["data"]:
                        res_data = item.get("spayee:resource", {})
                        title = res_data.get("spayee:title", "Course")
                        course_url_slug = res_data.get("spayee:courseUrl", item.get("_id"))
                        # Construct link with ID appended so extract_links can use it
                        course_id = item.get("_id")
                        link = f"{self.domain_url}/s/store/courses/description/{course_url_slug}?id={course_id}"
                        unique.append({"id": link, "title": title})
                    
                    if not unique:
                        return {"success": False, "error": "No enrolled courses found in API response."}
                        
                    self.courses = unique
                    return {"success": True, "courses": unique}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def extract_links(self, course_id):
        """Extract video/PDF links from a course page"""
        if not getattr(self, 'session_id', None):
            login_res = self._login_api()
            if not login_res.get("success"):
                print(f"Login failed before extraction: {login_res.get('error')}")
                return []

        self.total_videos = 0
        self.total_pdfs = 0
        self.raw_links = []
        self.title_map = {}
        self.id_map = {}
        
        try:
            import aiohttp
            import uuid
            
            # The course_id is either passed as a slug or ID. But since we modified _fetch_courses_api,
            # it might be the slug if it's the old format, or the ID.
            # If the user gives a URL like /s/store/courses/description/xyz, we need the course_id.
            # We can get courseId by fetching the description page and finding `courseId: "..."`.
            
            course_obj_id = course_id
            if "id=" in course_id:
                m = re.search(r'id=([a-f0-9]{24})', course_id)
                if m:
                    course_obj_id = m.group(1)
            elif "ganitank.com" in course_id or "description" in course_id:
                # Need to extract course ID. The HTML description page requires auth and doesn't contain the ID.
                # Let's map the slug back using the user's enrolled courses API.
                m = re.search(r'/description/([^?]+)', course_id)
                if m:
                    slug = m.group(1)
                    # fetch from API
                    import aiohttp
                    api_url = f"{self.domain_url}/s/mycourses/get?skip=0&limit=100&queryData=%7B%7D"
                    headers = {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                        "Accept": "application/json"
                    }
                    cookies = {}
                    if getattr(self, 'token', None):
                        cookies["jwt"] = self.token
                        cookies["c_ujwt"] = self.token
                    if getattr(self, 'session_id', None):
                        cookies["SESSIONID"] = self.session_id
                    
                    async with aiohttp.ClientSession(cookies=cookies) as session:
                        async with session.get(api_url, headers=headers) as resp:
                            if resp.status == 200:
                                data = await resp.json()
                                for item in data.get("data", {}).get("data", []):
                                    if item.get("spayee:resource", {}).get("spayee:courseUrl") == slug:
                                        course_obj_id = item.get("_id")
                                        break
                                        
                if course_obj_id == course_id:
                    # failed to map
                    return []
            else:
                # If it's a URL, extract the ID
                m = re.search(r'([a-f0-9]{24})', course_id)
                if m:
                    course_obj_id = m.group(1)
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "application/json"
            }
            cookies = {}
            if getattr(self, 'token', None):
                cookies["jwt"] = self.token
                cookies["c_ujwt"] = self.token
            if getattr(self, 'session_id', None):
                cookies["SESSIONID"] = self.session_id
                
            async with aiohttp.ClientSession(cookies=cookies) as session:
                # Fetch TOC
                toc_url = f"{self.domain_url}/s/store/course/{course_obj_id}/toc"
                async with session.get(toc_url, headers=headers) as resp:
                    if resp.status != 200:
                        return []
                    toc_data = await resp.json()
                    
                if "toc" not in toc_data:
                    return []
                    
                formatted_links = []
                
                # Helper to traverse TOC
                async def process_items(items, chapter_title):
                    for item in items:
                        item_type = item.get("type", "")
                        item_id = item.get("id", "")
                        item_title = item.get("title", "Item")
                        
                        full_title = f"({chapter_title}) {item_title}" if chapter_title else item_title
                        
                        if "items" in item:
                            await process_items(item["items"], item_title)
                            
                        elif item_type == "video":
                            # Fetch video URL
                            await asyncio.sleep(1.5) # Rate limit protection
                            v_url = f"{self.domain_url}/s/courses/{course_obj_id}/videos/{item_id}/get"
                            async with session.get(v_url, headers=headers) as vresp:
                                if vresp.status == 200:
                                    if 'application/json' not in vresp.headers.get('Content-Type', ''):
                                        print('Session expired or invalid for Spayee, got HTML instead of JSON.')
                                        continue
                                    vdata = await vresp.json()
                                    resource = vdata.get("spayee:resource", {})
                                    stream_url = resource.get("spayee:streamUrl")
                                    if stream_url:
                                        self.total_videos += 1
                                        token_val = self.token if getattr(self, 'token', None) else 'NO_TOKEN'
                                        
                                        key_b64 = ""
                                        try:
                                            key_url = stream_url.split('?')[0].rsplit('/', 1)[0] + '/k/timestamp'
                                            async with session.get(key_url, headers=headers) as kresp:
                                                if kresp.status == 200:
                                                    kblob = await kresp.read()
                                                    if len(kblob) == 64:
                                                        import base64
                                                        key_b64 = base64.b64encode(kblob).decode('utf-8')
                                        except:
                                            pass
                                            
                                        suffix = f"*{token_val}"
                                        if key_b64:
                                            suffix += f"*{key_b64}"
                                        formatted_links.append(f"{full_title} : {stream_url}{suffix}")
                        elif item_type == "pdf":
                            # Fetch PDF URL
                            await asyncio.sleep(1.5) # Rate limit protection
                            p_url = f"{self.domain_url}/s/courses/{course_obj_id}/pdfs/{item_id}/preview/url"
                            async with session.get(p_url, headers=headers) as presp:
                                if presp.status == 200:
                                    if 'application/json' not in presp.headers.get('Content-Type', ''):
                                        continue
                                    pdata = await presp.json()
                                    pdf_url = pdata.get("url")
                                    if pdf_url:
                                        self.total_pdfs += 1
                                        token_val = self.token if getattr(self, 'token', None) else 'NO_TOKEN'
                                        
                                        key_b64 = ""
                                        try:
                                            key_url = pdf_url.split('?')[0].rsplit('/', 1)[0] + '/k/timestamp'
                                            async with session.get(key_url, headers=headers) as kresp:
                                                if kresp.status == 200:
                                                    kblob = await kresp.read()
                                                    if len(kblob) == 64:
                                                        import base64
                                                        key_b64 = base64.b64encode(kblob).decode('utf-8')
                                        except:
                                            pass
                                            
                                        suffix = f"*{token_val}"
                                        if key_b64:
                                            suffix += f"*{key_b64}"
                                        formatted_links.append(f"{full_title} : {pdf_url}{suffix}")
                
                await process_items(toc_data["toc"], "")
                
                # Deduplicate
                unique_links = []
                seen = set()
                for flink in formatted_links:
                    if flink not in seen:
                        seen.add(flink)
                        unique_links.append(flink)
                        
                return unique_links
                
        except Exception as e:
            print(f"Extraction error: {e}")
            return []
