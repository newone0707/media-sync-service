import math
import time
from pyrogram.types import Message

# Store last updated time to avoid FloodWait limits
update_time = {}

async def progress_for_pyrogram(current, total, ud_type, message: Message, start_time):
    global update_time
    now = time.time()
    
    # Update every 5 seconds to prevent FloodWait errors
    if not (now - update_time.get(message.id, 0) > 5) and current != total:
        return
        
    update_time[message.id] = now

    try:
        percentage = current * 100 / total if total else 0
        speed = current / (now - start_time) if (now - start_time) > 0 else 0
        time_to_completion = round((total - current) / speed) if speed > 0 and total else 0
        
        # Build progress bar [██████░░░░]
        progress_str = "[{0}{1}] {2}%\n".format(
            ''.join(["█" for i in range(math.floor(percentage / 10))]),
            ''.join(["░" for i in range(10 - math.floor(percentage / 10))]),
            round(percentage, 2)
        )
        
        tmp = progress_str + \
            f"**{ud_type}**\n" + \
            f"**Speed:** {humanbytes(speed)}/s\n" + \
            f"**Done:** {humanbytes(current)} / {humanbytes(total) if total else 'Unknown'}\n" + \
            f"**ETA:** {time_formatter(time_to_completion)}"
            
        await message.edit_text(tmp)
    except Exception:
        pass

def humanbytes(size):
    if not size:
        return "0 B"
    power = 2**10
    n = 0
    Dic_powerN = {0: ' ', 1: 'K', 2: 'M', 3: 'G', 4: 'T'}
    while size > power:
        size /= power
        n += 1
    return str(round(size, 2)) + " " + Dic_powerN[n] + 'B'

def time_formatter(milliseconds: int) -> str:
    seconds, milliseconds = divmod(int(milliseconds), 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    tmp = ((str(days) + "d, ") if days else "") + \
        ((str(hours) + "h, ") if hours else "") + \
        ((str(minutes) + "m, ") if minutes else "") + \
        ((str(seconds) + "s, ") if seconds else "")
    return tmp[:-2] if tmp else "0s"
