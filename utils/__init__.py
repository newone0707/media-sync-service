import time
import math

import mmap
import os

def decrypt_file(file_path, key):
    if not os.path.exists(file_path):
        return False
    with open(file_path, "r+b") as f:
        num_bytes = min(28, os.path.getsize(file_path))
        with mmap.mmap(f.fileno(), length=num_bytes, access=mmap.ACCESS_WRITE) as mmapped_file:
            for i in range(num_bytes):
                mmapped_file[i] ^= ord(key[i]) if i < len(key) else i
    return True

def hrb(value, digits=2, delim="", postfix=""):
    if value is None:
        return None
    chosen_unit = "B"
    for unit in ("KB", "MB", "GB", "TB"):
        if value > 1000:
            value /= 1024
            chosen_unit = unit
        else:
            break
    return f"{value:.{digits}f}" + delim + chosen_unit + postfix

def hrt(seconds, precision=0):
    pieces = []
    value = int(seconds)
    
    if value >= 86400:
        days = value // 86400
        pieces.append(f"{days}d")
        value %= 86400
        
    if value >= 3600:
        hours = value // 3600
        pieces.append(f"{hours}h")
        value %= 3600
        
    if value >= 60:
        minutes = value // 60
        pieces.append(f"{minutes}m")
        value %= 60
        
    if value > 0 or not pieces:
        pieces.append(f"{value}s")
        
    if not precision:
        return "".join(pieces)
    return "".join(pieces[:precision])

async def progress_bar(current, total, msg, start_time):
    now = time.time()
    diff = now - start_time
    if diff < 1:
        return
        
    # Only update every 3 seconds to avoid FloodWait
    if not hasattr(msg, "last_update_time"):
        msg.last_update_time = 0
    if now - msg.last_update_time < 3:
        return
    msg.last_update_time = now
    
    perc = f"{current * 100 / total:.1f}%"
    elapsed_time = round(diff)
    speed = current / elapsed_time if elapsed_time > 0 else 0
    remaining_bytes = total - current
    eta = hrt(remaining_bytes / speed, precision=2) if speed > 0 else "-"
    
    sp = f"{hrb(speed)}/s"
    tot = hrb(total)
    cur = hrb(current)
    
    bar_length = 10
    completed = int(current * bar_length / total)
    remaining = bar_length - completed
    bar = "🟩" * completed + "⬜" * remaining
    
    text = f"**🚀 Uploading...**\n\n"
    text += f"**{bar}**\n"
    text += f"**Progress:** `{perc}`\n"
    text += f"**Speed:** `{sp}`\n"
    text += f"**Size:** `{cur} / {tot}`\n"
    text += f"**ETA:** `{eta}`"
    
    try:
        await msg.edit_text(text)
    except Exception:
        pass
