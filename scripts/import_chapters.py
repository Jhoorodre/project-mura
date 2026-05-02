import requests
import re
import json
import os
import html

PARENT_ID = "1G_saYSXmpC9XsXbAYyv9SqFUCpAvkLsN"
MANGA_SLUG = "ending-maker"
MANGA_NAME = "Ending Maker"

session = requests.Session()
session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"})

def get_drive_data(folder_id, use_embedded=False):
    if use_embedded:
        url = f"https://drive.google.com/embeddedfolderview?id={folder_id}"
    else:
        url = f"https://drive.google.com/drive/folders/{folder_id}"
        
    res = session.get(url)
    content = html.unescape(res.text)
    
    items = []
    seen_ids = set()
    
    if use_embedded:
        matches = re.findall(r'href="https://drive\.google\.com/drive/folders/([a-zA-Z0-9_-]{28,35})"[^>]*>.*?<div[^>]*>([^<]+)</div>', content, re.S)
        for item_id, name in matches:
            if item_id not in seen_ids:
                items.append({"id": item_id, "name": name.strip()})
                seen_ids.add(item_id)
        
        matches_files = re.findall(r'href="https://drive\.google\.com/file/d/([a-zA-Z0-9_-]{28,35})"[^>]*>.*?<div[^>]*>([^<]+)</div>', content, re.S)
        for item_id, name in matches_files:
            if item_id not in seen_ids:
                items.append({"id": item_id, "name": name.strip()})
                seen_ids.add(item_id)
    else:
        p1 = r'\["([a-zA-Z0-9_-]{28,35})",\["([a-zA-Z0-9_-]{28,35})"\]\s*,\s*"([^"]+)"'
        matches = re.findall(p1, content)
        for item_id, parent, name in matches:
            if parent == folder_id and item_id not in seen_ids:
                items.append({"id": item_id, "name": name})
                seen_ids.add(item_id)
        
        if not items:
            matches = re.findall(r'data-id="([a-zA-Z0-9_-]{28,35})".*?data-tooltip="([^"]+)"', content, re.S)
            for item_id, tooltip in matches:
                if item_id not in seen_ids:
                    name = re.sub(r' (Shared folder|Image|Folder|Video)$', '', tooltip)
                    items.append({"id": item_id, "name": name})
                    seen_ids.add(item_id)

    return items

def main():
    print(f"Fetching chapters from folder {PARENT_ID}...")
    folders = get_drive_data(PARENT_ID, use_embedded=False)
    folders_emb = get_drive_data(PARENT_ID, use_embedded=True)
    
    all_folders = folders + folders_emb
    seen_ids = set()
    unique_folders = []
    for f in all_folders:
        if f['id'] not in seen_ids:
            unique_folders.append(f)
            seen_ids.add(f['id'])
    
    chapters = []
    for f in unique_folders:
        match = re.search(r'Cap\s*([0-9.]+)', f['name'], re.I)
        if match:
            num_str = match.group(1)
            # Remove leading zeros but keep decimals
            clean_num = str(float(num_str)).replace('.0', '') if '.' in num_str else str(int(num_str))
            
            chapters.append({
                "id": f['id'],
                "name": f['name'],
                "num_str": clean_num,
                "num_float": float(num_str)
            })
    
    # Deduplicate by number
    chapters_dict = {}
    for c in chapters:
        if c['num_float'] not in chapters_dict:
            chapters_dict[c['num_float']] = c
            
    chapters = sorted(chapters_dict.values(), key=lambda x: x['num_float'])
    
    print(f"Found {len(chapters)} unique chapters.")
    if not chapters:
        return

    for i, cap in enumerate(chapters):
        cap_num = cap['num_str']
        # Folder slug standard: cap1, cap2, cap67_5
        cap_slug = f"cap{cap_num}".replace('.', '_')
        
        print(f"Processing Capítulo {cap_num}...")
        
        files = get_drive_data(cap['id'], use_embedded=False)
        if len(files) < 2:
            files_emb = get_drive_data(cap['id'], use_embedded=True)
            files.extend(files_emb)
            
        seen_file_ids = set()
        unique_files = []
        for f in files:
            if f['id'] not in seen_file_ids:
                unique_files.append(f)
                seen_file_ids.add(f['id'])
            
        images = []
        for f in unique_files:
            if re.search(r'\.(jpg|jpeg|png|webp|bmp|gif)$', f['name'], re.I) or f['name'].isdigit():
                images.append(f)
        
        images.sort(key=lambda x: [int(s) if s.isdigit() else s.lower() for s in re.split('([0-9]+)', x['name'])])
        
        if not images:
            print(f"  Warning: No images found in {cap['name']}")
            continue
            
        dest_dir = f"assets/mangas/{MANGA_SLUG}/{cap_slug}"
        os.makedirs(dest_dir, exist_ok=True)
        
        image_urls = [f"https://drive.usercontent.google.com/uc?id={img['id']}&export=download" for img in images]
        with open(f"{dest_dir}/images.json", "w") as j:
            json.dump(image_urls, j, indent=2)
            
        next_href = f"/{MANGA_SLUG}/cap{chapters[i+1]['num_str']}/" if i + 1 < len(chapters) else ""
        
        md_content = f"""---
layout: reader
title: "Capítulo {cap_num}"
manga: "{MANGA_SLUG}"
manga_slug: "{MANGA_SLUG}"
capitulo: {cap_num}
es_primero: {"true" if i == 0 else "false"}
es_ultimo: {"true" if i == len(chapters)-1 else "false"}
permalink: /{MANGA_SLUG}/cap{cap_num}/
return_to: /{MANGA_SLUG}/
images_json: {dest_dir}/images.json
use_main_css: true
next_href: {next_href}
---
"""
        with open(f"_{MANGA_SLUG}/cap{cap_num}-{MANGA_SLUG}.md", "w") as m:
            m.write(md_content)

    print(f"Done! Standardized {len(chapters)} chapters. Latest: {chapters[-1]['num_str']}.")

if __name__ == "__main__":
    main()
