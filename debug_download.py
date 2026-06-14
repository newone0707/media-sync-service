import asyncio
from plugins.uploader import download_m3u8

async def main():
    appx_url = "https://static-trans-v1.appx.co.in/videos/vishalkhodifad-data/526248-1706260805/encrypted-401185/360p/encrypted.mp4?URLPrefix=aHR0cHM6Ly9zdGF0aWMtdHJhbnMtdjEuYXBweC5jby5pbi92aWRlb3MvdmlzaGFsa2hvZGlmYWQtZGF0YS81MjYyNDgtMTcwNjI2MDgwNS9lbmNyeXB0ZWQtNDAxMTg1LzM2MHAvZW5jcnlwdGVkLm1wNA&Expires=1781367043&KeyName=appx-pdf-keyset&Signature=kC7GdQXeXfP3K5ve5rDqyJ2ZUnC5fRcxi88X6JqIib9WplmuS6cxypOPoggoNpIRRMoPqgjmaB0xwPLZrE3ZAQ*RI5we8T5/ZXsZp4kGpNMpw==:ZmVkY2JhOTg3NjU0MzIxMA=="
    cp_url = "https://media-cdn.classplusapp.com/5013/cc/ebacecaed2e243cbbdea98adcf5c1d4e-5y/master.m3u8?contentHashId=U2FsdGVkX1%2B2JKddYrXTXbgR9Ep9sRisOcEXG%2BjQ5ZQ%3D&token=eyJhbGciOiJIUzM4NCIsInR5cCI6IkpXVCJ9.eyJpZCI6MTU0Njc1ODkwLCJvcmdJZCI6NTAxMywidHlwZSI6MSwibW9iaWxlIjoiOTE4NjI0OTIyOTQwIiwibmFtZSI6IkFycGl0IEFycGl0IiwiZW1haWwiOiJhcnBpdHBhdGlsNDY2QGdtYWlsLmNvbSIsImlzSW50ZXJuYXRpb25hbCI6MCwiZGVmYXVsdExhbmd1YWdlIjoiRU4iLCJjb3VudHJ5Q29kZSI6IklOIiwiY291bnRyeUlTTyI6IjkxIiwidGltZXpvbmUiOiJHTVQrNTozMCIsImlzRGl5Ijp0cnVlLCJvcmdDb2RlIjoiZHF4a2wiLCJpc0RpeVN1YmFkbWluIjowLCJmaW5nZXJwcmludElkIjoiMDk3N2QxNzIwZDU5YWEzMmRkOWU2ODA5YzVlNjEzOGRmYjM5ZjBiMDYyMTc3NjIxYTNkODAwMjQwMDY4ZWM4ZSIsImlhdCI6MTc4MDkzMjM5NCwiZXhwIjoxNzgxNTM3MTk0fQ.OldLy51QjElqLbRx-qt3_kw05Jwavxcz2zHayMgkDdLE56Uuoke8jRNZQ3Ul2t_e"
    
    import traceback
    
    print("Testing Appx:")
    res = await download_m3u8(appx_url.rsplit(':', 1)[0], "appx_test.mp4", "https://vishalkhodifadapi.classx.co.in/")
    print("Appx result:", res)

if __name__ == "__main__":
    asyncio.run(main())
