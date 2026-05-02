import json
import yaml
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

class ProjectManager:
    def __init__(self, root_path: str = "."):
        self.root = Path(root_path)
        self.catalogo_path = self.root / "catalogo.json"
        self.config_path = self.root / "_config.yml"

    def load_catalogo(self) -> Dict[str, Any]:
        if not self.catalogo_path.exists():
            return {"items": []}
        try:
            with open(self.catalogo_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"items": []}

    def save_catalogo(self, data: Dict[str, Any]):
        with open(self.catalogo_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def load_config(self) -> Dict[str, Any]:
        if not self.config_path.exists():
            return {}
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception:
            return {}

    def save_config(self, data: Dict[str, Any]):
        with open(self.config_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)

    def add_manga(self, manga_id: str, title: str, section: str, tags: List[str], portada: str, synopsis: str = "", authors: List[str] = [], artists: List[str] = [], latest: str = "Novo"):
        # 1. Update catalogo.json
        cat = self.load_catalogo()
        for item in cat.get("items", []):
            if item["mangaId"] == manga_id:
                # Update existing instead of just returning? 
                # For safety in bug hunt, let's update.
                item.update({
                    "title": title,
                    "portada": portada,
                    "tags": tags,
                    "seccion": section
                })
                break
        else:
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
        
        # Ensure it's in collections
        config["collections"][manga_id] = {
            "output": True,
            "permalink": f"/{manga_id}/:name/"
        }
        
        if "defaults" not in config:
            config["defaults"] = []
            
        # Avoid duplicate defaults
        exists = any(d.get("scope", {}).get("type") == manga_id for d in config["defaults"])
        if not exists:
            config["defaults"].append({
                "scope": {"type": manga_id},
                "values": {"layout": "caps"}
            })
        self.save_config(config)

        # 3. Create directory
        manga_dir = self.root / f"_{manga_id}"
        manga_dir.mkdir(exist_ok=True)
        
        # 4. Create inicio.md
        inicio_path = manga_dir / "inicio.md"
        date_str = datetime.now().strftime("%Y-%m-%d")
        
        frontmatter = {
            "layout": "caps",
            "title": title,
            "date": date_str,
            "series": manga_id,
            "portada": portada,
            "sinopsis": synopsis,
            "autor": ", ".join(authors) if authors else "—",
            "artista": ", ".join(artists) if artists else "—",
            "generos": tags,
            "estado": "Activo" if section == "activos" else "—",
            "anio": datetime.now().year,
            "editorial": "—",
            "links_descarga": [],
            "show_links_en_ficha": False,
            "use_theme": True
        }
        
        with open(inicio_path, "w", encoding="utf-8") as f:
            f.write("---\n")
            yaml.safe_dump(frontmatter, f, allow_unicode=True, sort_keys=False)
            f.write("---\n")

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
        # Standard: only remove if directory is named exactly as expected
        manga_dir = self.root / f"_{manga_id}"
        if manga_dir.exists() and manga_dir.is_dir():
            import shutil
            shutil.rmtree(manga_dir)
            
        assets_dir = self.root / "assets" / "mangas" / manga_id
        if assets_dir.exists() and assets_dir.is_dir():
            import shutil
            shutil.rmtree(assets_dir)
            
        print(f"Manga {manga_id} removed completely.")
