import json
import yaml
import os
from pathlib import Path
from typing import List, Dict, Any, Optional

class ProjectManager:
    def __init__(self, root_path: str = "."):
        self.root = Path(root_path)
        self.catalogo_path = self.root / "catalogo.json"
        self.config_path = self.root / "_config.yml"

    def load_catalogo(self) -> Dict[str, Any]:
        if not self.catalogo_path.exists():
            return {"items": []}
        with open(self.catalogo_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def save_catalogo(self, data: Dict[str, Any]):
        with open(self.catalogo_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def load_config(self) -> Dict[str, Any]:
        if not self.config_path.exists():
            return {}
        with open(self.config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def save_config(self, data: Dict[str, Any]):
        with open(self.config_path, "w", encoding="utf-8") as f:
            # We use a custom dumper to keep comments if possible, but safe_load/dump is standard
            yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)

    def add_manga(self, manga_id: str, title: str, section: str, tags: List[str], portada: str, latest: str = "Novo"):
        # 1. Update catalogo.json
        cat = self.load_catalogo()
        # Check if exists
        for item in cat["items"]:
            if item["mangaId"] == manga_id:
                print(f"Manga {manga_id} already exists in catalog.")
                return
        
        new_item = {
            "mangaId": manga_id,
            "title": title,
            "post_url": f"/{manga_id}/inicio",
            "portada": portada,
            "tags": tags,
            "latest": latest,
            "seccion": section
        }
        cat["items"].insert(0, new_item)
        self.save_catalogo(cat)

        # 2. Update _config.yml
        config = self.load_config()
        if "collections" not in config:
            config["collections"] = {}
        
        config["collections"][manga_id] = {
            "output": True,
            "permalink": f"/{manga_id}/:name/"
        }
        
        if "defaults" not in config:
            config["defaults"] = []
            
        config["defaults"].append({
            "scope": {"type": manga_id},
            "values": {"layout": "caps"}
        })
        self.save_config(config)

        # 3. Create directory
        manga_dir = self.root / f"_{manga_id}"
        manga_dir.mkdir(exist_ok=True)
        
        # 4. Create inicio.md (landing page)
        # To be implemented with detailed fields
        print(f"Manga {title} added successfully.")

    def delete_manga(self, manga_id: str):
        # 1. Remove from catalogo.json
        cat = self.load_catalogo()
        cat["items"] = [item for item in cat["items"] if item["mangaId"] != manga_id]
        self.save_catalogo(cat)

        # 2. Remove from _config.yml
        config = self.load_config()
        if "collections" in config and manga_id in config["collections"]:
            del config["collections"][manga_id]
        
        if "defaults" in config:
            config["defaults"] = [d for d in config["defaults"] if d.get("scope", {}).get("type") != manga_id]
        self.save_config(config)

        # 3. Delete directory and assets
        # Be careful with recursive deletion
        manga_dir = self.root / f"_{manga_id}"
        assets_dir = self.root / "assets" / "mangas" / manga_id
        # Note: We should probably move them to a 'trash' or just report.
        print(f"Manga {manga_id} removed from config and catalog.")
