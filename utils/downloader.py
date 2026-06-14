import os
import yt_dlp
import asyncio
from pyrogram.types import Message

async def download_video(url: str, output_dir: str, file_name: str, message: Message, headers: dict = None) -> str:
    """
    Downloads a video using yt-dlp and returns the file path.
    """
    os.makedirs(output_dir, exist_ok=True)
    file_path = os.path.join(output_dir, f"{file_name}.%(ext)s")
    
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': file_path,
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
    }
    
    if headers:
        ydl_opts['http_headers'] = headers
    
    # Run yt-dlp in a separate thread so it doesn't block the async loop
    def run_ytdlp():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return ydl.prepare_filename(info)

    await message.edit_text("⏳ **Downloading video...**\n(This might take a while depending on file size)")
    loop = asyncio.get_event_loop()
    
    try:
        downloaded_file = await loop.run_in_executor(None, run_ytdlp)
        return downloaded_file
    except Exception as e:
        raise Exception(f"Download Failed: {str(e)}")

async def download_pdf(url: str, output_dir: str, file_name: str, message: Message) -> str:
    """
    Downloads a PDF file and updates progress.
    """
    import time
    import aiohttp
    import aiofiles
    from utils import progress_bar
    
    os.makedirs(output_dir, exist_ok=True)
    file_path = os.path.join(output_dir, f"{file_name}.pdf")
    
    start_time = time.time()
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status != 200:
                raise Exception(f"Failed to download PDF, status: {response.status}")
                
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            async with aiofiles.open(file_path, 'wb') as f:
                async for chunk in response.content.iter_chunked(1024 * 1024): # 1MB chunks
                    if chunk:
                        await f.write(chunk)
                        downloaded += len(chunk)
                        if total_size:
                            await progress_bar(downloaded, total_size, message, start_time)
                            
    return file_path
