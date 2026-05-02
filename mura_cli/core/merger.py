import shutil
import os
from pathlib import Path
from typing import List

class ChapterMerger:
    def merge_folders(self, source_dirs: List[str], target_dir: str):
        """
        Merges images from multiple folders into a single target folder.
        Useful for combining joint chapters or split volumes.
        """
        target_path = Path(target_dir)
        target_path.mkdir(parents=True, exist_ok=True)
        
        current_index = 1
        for s_dir in source_dirs:
            s_path = Path(s_dir)
            if not s_path.exists():
                print(f"Warning: Source directory {s_dir} does not exist.")
                continue
                
            # Get files sorted
            files = sorted([f for f in s_path.iterdir() if f.is_file()])
            for f in files:
                # Extension
                ext = f.suffix
                new_name = f"{current_index:03d}{ext}"
                shutil.copy2(f, target_path / new_name)
                current_index += 1
        
        print(f"Merged {current_index - 1} images into {target_dir}.")

    def merge_json(self, json_files: List[str], target_json: str):
        """
        Merges multiple images.json contents.
        """
        merged_pages = []
        for j_file in json_files:
            if not os.path.exists(j_file):
                continue
            with open(j_file, "r") as f:
                data = json.load(f)
                if isinstance(data, list):
                    merged_pages.extend(data)
                elif isinstance(data, dict) and "pages" in data:
                    merged_pages.extend(data["pages"])
        
        with open(target_json, "w") as f:
            json.dump(merged_pages, f, indent=2)
        
        print(f"Merged JSON data into {target_json}.")
