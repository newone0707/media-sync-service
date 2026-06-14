import asyncio
import os
from utils import decrypt_file
import requests

def sync_download(url, output_path, referer):
    try:
        r = requests.get(url, stream=True, headers={'User-Agent': 'Mozilla/5.0', 'Referer': referer, 'Origin': referer})
        r.raise_for_status()
        with open(output_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    except Exception as e:
        print(f"Direct Download Error: {e}")
        return False

def test():
    # Test link from earlier
    link = "https://static-trans-v2.appx.co.in/videos/sciencemagnet-data/3128597-1768636299/encrypted-869058/720p/encrypted.mkv?URLPrefix=aHR0cHM6Ly9zdGF0aWMtdHJhbnMtdjIuYXBweC5jby5pbi92aWRlb3Mvc2NpZW5jZW1hZ25ldC1kYXRhLzMxMjg1OTctMTc2ODYzNjI5OS9lbmNyeXB0ZWQtODY5MDU4LzcyMHAvZW5jcnlwdGVkLm1rdg&Expires=1781294284&KeyName=appx-pdf-keyset&Signature=uChLgha5z2EQXkNnbzXSRJ-ICxylGLR4MAdxccbL-Dgk7inn8codPo83BhtyDSio_hpDc7wLWnOsVqQXa7ihCg*3cc515a4eb3df4b9"
    base_url = "https://sciencemagnetapi.classx.co.in/"
    
    aes_key = None
    if "*" in link:
        link, aes_key = link.split("*", 1)
        
    mp4_path = "test_video.mp4"
    referer = base_url if base_url.endswith('/') else base_url + '/'
    
    print("Downloading...")
    success = sync_download(link, mp4_path, referer)
    print(f"Download success: {success}")
    if success and aes_key and os.path.exists(mp4_path):
        print("Decrypting...")
        decrypted = decrypt_file(mp4_path, aes_key)
        print(f"Decrypt success: {decrypted}")
        print("Size:", os.path.getsize(mp4_path))
        
test()
