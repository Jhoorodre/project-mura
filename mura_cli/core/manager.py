import json
import yaml
import os
import requests
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

class ProjectManager:
    def __init__(self, root_path: str = "."):
        self.root = Path(root_path)
        self.catalogo_path = self.root / "catalogo.json"
        self.config_path = self.root / "_config.yml"

    def download_image(self, url: str, manga_id: str) -> str:
        """
        Downloads a cover image from a URL and returns the local path.
        """
        if not url or not url.startswith("http"):
            return url
        
        img_dir = self.root / "assets" / "img"
        img_dir.mkdir(parents=True, exist_ok=True)
        
        # Get extension
        ext = ".jpg"
        if ".png" in url.lower(): ext = ".png"
        elif ".webp" in url.lower(): ext = ".webp"
        
        filename = f"{manga_id}-cover{ext}"
        target_path = img_dir / filename
        
        try:
            response = requests.get(url, timeout=15)
            if response.status_code == 200:
                with open(target_path, "wb") as f:
                    f.write(response.content)
                return f"/assets/img/{filename}"
        except Exception as e:
            print(f"Error downloading image: {e}")
            
        return url

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
        # 0. Sanitize manga_id (slug)
        manga_id = manga_id.lower().replace(" ", "-").replace("_", "-")
        
        # 1. Download cover locally
        local_portada = self.download_image(portada, manga_id)

        # 2. Update catalogo.json
        cat = self.load_catalogo()
        for item in cat.get("items", []):
            if item["mangaId"] == manga_id:
                item.update({
                    "title": title,
                    "portada": local_portada,
                    "tags": tags,
                    "seccion": section
                })
                break
        else:
            new_item = {
                "mangaId": manga_id,
                "title": title,
                "post_url": f"/{manga_id}/inicio",
                "portada": local_portada,
                "tags": tags,
                "latest": latest,
                "seccion": section
            }
            cat["items"].insert(0, new_item)
        self.save_catalogo(cat)

        # 3. Update _config.yml
        config = self.load_config()
        if "collections" not in config: config["collections"] = {}
        config["collections"][manga_id] = {"output": True, "permalink": f"/{manga_id}/:name/"}
        
        if "defaults" not in config: config["defaults"] = []
        exists = any(d.get("scope", {}).get("type") == manga_id for d in config["defaults"])
        if not exists:
            config["defaults"].append({"scope": {"type": manga_id}, "values": {"layout": "caps"}})
        self.save_config(config)

        # 4. Create directory
        manga_dir = self.root / f"_{manga_id}"
        manga_dir.mkdir(exist_ok=True)
        
        # 5. Create inicio.md
        inicio_path = manga_dir / "inicio.md"
        date_str = datetime.now().strftime("%Y-%m-%d")
        
        frontmatter = {
            "layout": "caps",
            "title": title,
            "date": date_str,
            "series": manga_id,
            "portada": local_portada,
            "sinopsis": synopsis or "",
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

        print(f"Manga {title} processed successfully with local cover.")

    def delete_manga(self, manga_id: str):
        cat = self.load_catalogo()
        
        # Find the cover path to delete
        cover_path = None
        for item in cat.get("items", []):
            if item.get("mangaId") == manga_id:
                cover_path = item.get("portada")
                break

        cat["items"] = [item for item in cat.get("items", []) if item.get("mangaId") != manga_id]
        self.save_catalogo(cat)

        config = self.load_config()
        if "collections" in config and manga_id in config["collections"]: del config["collections"][manga_id]
        if "defaults" in config: config["defaults"] = [d for d in config["defaults"] if d.get("scope", {}).get("type") != manga_id]
        self.save_config(config)

        # Cleanup folders
        import shutil
        shutil.rmtree(self.root / f"_{manga_id}", ignore_errors=True)
        shutil.rmtree(self.root / "assets" / "mangas" / manga_id, ignore_errors=True)
        
        # Cleanup cover image
        if cover_path and cover_path.startswith("/assets/img/"):
            # Remove leading slash to make it relative to root
            local_cover_path = self.root / cover_path.lstrip("/")
            if local_cover_path.exists() and local_cover_path.is_file():
                try:
                    os.remove(local_cover_path)
                except Exception as e:
                    print(f"Failed to remove cover image: {e}")
        
        print(f"Manga {manga_id} removed.")
