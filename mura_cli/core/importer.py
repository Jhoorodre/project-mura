import requests
import re
import json
import os
import html
from typing import List, Dict, Any

class DriveImporter:
    def __init__(self, session=None):
        self.session = session or requests.Session()
        self.session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"})

    def get_drive_data(self, folder_id: str, use_embedded: bool = False) -> List[Dict[str, str]]:
        # Sanitize folder_id (extract just the ID if a full URL or query params were pasted)
        match = re.search(r'([a-zA-Z0-9_-]{28,35})', folder_id)
        if match:
            folder_id = match.group(1)

        if use_embedded:
            url = f"https://drive.google.com/embeddedfolderview?id={folder_id}"
        else:
            url = f"https://drive.google.com/drive/folders/{folder_id}"
            
        res = self.session.get(url)
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
                        
            # Aggressive fallback for >50 items in standard view
            chunks = re.findall(r'AF_initDataCallback\({key:.*?, hash:.*?, data:(.*?), sideChannel:.*?}\);', content)
            for chunk in chunks:
                try:
                    potential_matches = re.findall(r'["\']([a-zA-Z0-9_-]{28,35})["\'],\[["\']([a-zA-Z0-9_-]{28,35})["\']\],["\']([^"\']+)["\']', chunk)
                    for item_id, parent, name in potential_matches:
                        if parent == folder_id and item_id not in seen_ids:
                            items.append({"id": item_id, "name": name})
                            seen_ids.add(item_id)
                except Exception:
                    continue

        return items

    def import_chapters(self, parent_id: str, manga_slug: str, root_path: str = "."):
        print(f"Scanning folder {parent_id} for chapters...")
        # Try multiple views to maximize results
        all_items = []
        all_items.extend(self.get_drive_data(parent_id, use_embedded=False))
        all_items.extend(self.get_drive_data(parent_id, use_embedded=True))
        
        seen_ids = set()
        unique_folders = []
        for f in all_items:
            if f['id'] not in seen_ids:
                unique_folders.append(f)
                seen_ids.add(f['id'])
        
        chapters = []
        for f in unique_folders:
            # Match Cap 000, Capítulo 1, etc.
            match = re.search(r'(?:Cap|Capítulo|Chapter)\s*([0-9.]+)', f['name'], re.I)
            if match:
                num_str = match.group(1)
                try:
                    num_float = float(num_str)
                    clean_num = str(num_float).replace('.0', '') if '.' in num_str else str(int(num_float))
                    chapters.append({
                        "id": f['id'],
                        "name": f['name'],
                        "num_str": clean_num,
                        "num_float": num_float
                    })
                except ValueError:
                    continue
        
        if not chapters:
            print("No chapters detected. Listing items found for debugging:")
            for item in unique_folders[:10]:
                print(f"  - {item['name']} (ID: {item['id']})")
            return None

        # Deduplicate and sort
        chapters_dict = {c['num_float']: c for c in chapters}
        chapters = sorted(chapters_dict.values(), key=lambda x: x['num_float'])
        
        print(f"Found {len(chapters)} unique chapters.")
        
        for i, cap in enumerate(chapters):
            cap_num = cap['num_str']
            cap_slug = f"cap{cap_num}".replace('.', '_')
            print(f"Processing Capítulo {cap_num}...")
            
            # Get images for this chapter
            images_data = []
            images_data.extend(self.get_drive_data(cap['id'], use_embedded=False))
            images_data.extend(self.get_drive_data(cap['id'], use_embedded=True))
            
            seen_img_ids = set()
            images = []
            for img in images_data:
                if img['id'] not in seen_img_ids:
                    if re.search(r'\.(jpg|jpeg|png|webp|bmp|gif)$', img['name'], re.I) or img['name'].isdigit():
                        images.append(img)
                        seen_img_ids.add(img['id'])
            
            # Sort images by name
            images.sort(key=lambda x: [int(s) if s.isdigit() else s.lower() for s in re.split('([0-9]+)', x['name'])])
            
            if not images:
                print(f"  Warning: No images found in {cap['name']}")
                continue
                
            dest_dir = f"assets/mangas/{manga_slug}/{cap_slug}"
            os.makedirs(os.path.join(root_path, dest_dir), exist_ok=True)
            
            image_urls = [f"https://drive.usercontent.google.com/uc?id={img['id']}&export=download" for img in images]
            with open(os.path.join(root_path, dest_dir, "images.json"), "w") as j:
                json.dump(image_urls, j, indent=2)
                
            next_href = f"/{manga_slug}/cap{chapters[i+1]['num_str']}/" if i + 1 < len(chapters) else ""
            
            md_content = f"""---
layout: reader
title: "Capítulo {cap_num}"
manga: "{manga_slug}"
manga_slug: "{manga_slug}"
capitulo: {cap_num}
es_primero: {"true" if i == 0 else "false"}
es_ultimo: {"true" if i == len(chapters)-1 else "false"}
permalink: /{manga_slug}/cap{cap_num}/
return_to: /{manga_slug}/
images_json: {dest_dir}/images.json
use_main_css: true
next_href: {next_href}
---
"""
            manga_folder = os.path.join(root_path, f"_{manga_slug}")
            os.makedirs(manga_folder, exist_ok=True)
            with open(os.path.join(manga_folder, f"cap{cap_num}-{manga_slug}.md"), "w") as m:
                m.write(md_content)

        return chapters[-1]['num_str'] if chapters else None
