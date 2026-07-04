import re
import os
from pyrogram import filters
from pyrogram.handlers import MessageHandler
# Aapke bot ke core imports (path aapke repo ke hisab se adjust karein)
from bot import bot, config_dict, CustomFilters # CustomFilters jisme owner check ho

# Dictionary to store the global format set by owner/dev
# (Ideally ise Database me save karein taaki bot restart pe reset na ho, par abhi dict use kar rahe hain)
renaming_operations = {
    "format": None  # Default is None, matlab normal leech working
}

# --- AAPKE PATTERNS ---
pattern1 = re.compile(r'S(\d+)(?:E|EP)(\d+)', re.IGNORECASE)
pattern2 = re.compile(r'S(\d+)\s*(?:E|EP|-\s*EP)(\d+)', re.IGNORECASE)
pattern3 = re.compile(r'(?:[([<{]?\s*(?:E|EP)\s*(\d+)\s*[)\]>}]?)', re.IGNORECASE)
pattern3_2 = re.compile(r'(?:\s*-\s*(\d+)\s*)')
pattern4 = re.compile(r'S(\d+)[^\d]*(\d+)', re.IGNORECASE)
patternX = re.compile(r'(\d+)')

pattern5 = re.compile(r'\b(?:.*?(\d{3,4}[^\dp]*p).*?|.*?(\d{3,4}p))\b', re.IGNORECASE)
pattern6 = re.compile(r'[([<{]?\s*4k\s*[)\]>}]?', re.IGNORECASE)
pattern7 = re.compile(r'[([<{]?\s*2k\s*[)\]>}]?', re.IGNORECASE)
pattern8 = re.compile(r'[([<{]?\s*HdRip\s*[)\]>}]?|\bHdRip\b', re.IGNORECASE)
pattern9 = re.compile(r'[([<{]?\s*4kX264\s*[)\]>}]?', re.IGNORECASE)
pattern10 = re.compile(r'[([<{]?\s*4kx265\s*[)\]>}]?', re.IGNORECASE)

pattern_audio = re.compile(r'(Dual Audio|Hindi|English|Tamil|Telugu|AAC|EAC3|DTS|DD5\.1)', re.IGNORECASE)

# --- EXTRACTION LOGIC ---
def extract_quality(filename):
    match5 = re.search(pattern5, filename)
    if match5: return match5.group(1) or match5.group(2)
    if re.search(pattern6, filename): return "4K"
    if re.search(pattern7, filename): return "2K"
    if re.search(pattern8, filename): return "HDRip"
    if re.search(pattern9, filename): return "4Kx264"
    if re.search(pattern10, filename): return "4Kx265"
    return ""

def extract_season_number(filename):
    for p in [pattern1, pattern2, pattern4]:
        match = re.search(p, filename)
        if match: return match.group(1).zfill(2)
    return ""
    
def extract_episode_number(filename):    
    for p in [pattern1, pattern2, pattern4]:
        match = re.search(p, filename)
        if match: return match.group(2).zfill(2)
        
    for p in [pattern3, pattern3_2, patternX]:
        match = re.search(p, filename)
        if match: return match.group(1).zfill(2)
    return ""

def extract_audio(filename):
    match = re.search(pattern_audio, filename)
    if match: return match.group(1).title()
    return ""

def extract_title(filename):
    title = filename
    patterns_to_remove = [pattern1, pattern2, pattern3, pattern3_2, pattern4, pattern5, pattern6, pattern7, pattern8, pattern9, pattern10, pattern_audio]
    for p in patterns_to_remove:
        title = re.sub(p, '', title)
    # Cleanup special chars and extra spaces
    title = re.sub(r'[\[\]\(\)\{\}<>]', '', title)
    title = title.replace('.', ' ').replace('-', ' ').strip()
    return re.sub(r'\s+', ' ', title)

def apply_auto_rename(original_filename, user_custom_name=None):
    """
    Returns the new filename based on hierarchy:
    1. Custom name passed via cmd (-n) overrides everything.
    2. Owner Format is applied if set.
    3. Default original name if nothing is set.
    """
    if user_custom_name:
        return user_custom_name
        
    global_format = renaming_operations.get("format")
    if not global_format:
        return original_filename

    ext = os.path.splitext(original_filename)[1]
    name_without_ext = os.path.splitext(original_filename)[0]
    
    season = extract_season_number(name_without_ext)
    episode = extract_episode_number(name_without_ext)
    quality = extract_quality(name_without_ext)
    audio = extract_audio(name_without_ext)
    title = extract_title(name_without_ext)
    
    new_name = global_format
    new_name = new_name.replace("{title}", title)
    
    # Handle optional parts (if missing, remove their tags cleanly)
    if season: new_name = new_name.replace("{season}", season)
    else: new_name = re.sub(r'S?\{season\}', '', new_name, flags=re.IGNORECASE)
        
    if episode: new_name = new_name.replace("{episode}", episode)
    else: new_name = re.sub(r'E?\{episode\}', '', new_name, flags=re.IGNORECASE)
        
    if quality: new_name = new_name.replace("{quality}", quality)
    else: new_name = new_name.replace("{quality}", "")
        
    if audio: new_name = new_name.replace("{audio}", audio)
    else: new_name = new_name.replace("{audio}", "")
        
    # Final cleanup (empty brackets)
    new_name = re.sub(r'\[\s*\]|\(\s*\)|\{\s*\}', '', new_name)
    new_name = re.sub(r'\s+', ' ', new_name).strip()
    
    # Ensure it's not totally empty (edge case)
    if not new_name.strip():
        return original_filename
        
    return new_name + ext

# --- COMMAND TO SET FORMAT (ONLY FOR OWNER/DEV) ---
# Yaha pe CustomFilters.owner use kar sakte ho ya apni user id hardcode/config match.
async def set_rename_format(client, message):
    user_id = message.from_user.id
    # Validate Owner / Dev
    if user_id not in [config_dict.get('OWNER_ID'), config_dict.get('DEV_ID', 0)]:
        return await message.reply("Only Owner or Dev can use this command.")
        
    text = message.text.split(' ', 1)
    if len(text) > 1:
        new_format = text[1].strip()
        if new_format.lower() == "off":
            renaming_operations["format"] = None
            await message.reply("Auto-Rename globally **Disabled**.")
        else:
            renaming_operations["format"] = new_format
            await message.reply(f"Auto-Rename format globally set to:\n`{new_format}`\n\nExample Output for `[S{{season}}E{{episode}}] {{title}} [{{quality}}]`: `[S01E02] My Show [1080p]`")
    else:
        current = renaming_operations.get("format", "Not Set")
        await message.reply(f"Current Auto-Rename Format: `{current}`\n\nUsage: `/setformat [S{{season}}E{{episode}}] {{title}} [{{quality}}]`\nTo disable: `/setformat off`")

bot.add_handler(MessageHandler(set_rename_format, filters=filters.command("setformat")))
