import requests
from typing import Dict, Any, Optional, List
import os
import json
from pathlib import Path

class MetadataFetcher:
    ANILIST_URL = "https://graphql.anilist.co"

    def fetch_anilist(self, search: str) -> Optional[Dict[str, Any]]:
        """
        Fetches manga metadata from AniList.
        """
        query = """
        query ($search: String) {
          Media (search: $search, type: MANGA) {
            title {
              romaji
              english
              native
            }
            description
            genres
            coverImage {
              extraLarge
            }
            startDate {
              year
            }
            staff {
              edges {
                role
                node {
                  name {
                    full
                  }
                }
              }
            }
          }
        }
        """
        variables = {"search": search}
        try:
            response = requests.post(self.ANILIST_URL, json={'query': query, 'variables': variables}, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if not data.get("data") or not data["data"].get("Media"):
                    return None
                
                media = data["data"]["Media"]
                
                authors = []
                artists = []
                for edge in media.get("staff", {}).get("edges", []):
                    role = edge.get("role", "").lower()
                    name = edge.get("node", {}).get("name", {}).get("full")
                    if "story" in role or "writer" in role:
                        authors.append(name)
                    if "art" in role or "illustrator" in role:
                        artists.append(name)
                
                return {
                    "source": "AniList",
                    "title": media["title"]["english"] or media["title"]["romaji"],
                    "synopsis": (media.get("description") or "").replace("<br>", "\n").replace("<i>", "").replace("</i>", "").replace("<b>", "").replace("</b>", ""),
                    "genres": media.get("genres", []),
                    "portada": media.get("coverImage", {}).get("extraLarge"),
                    "year": media.get("startDate", {}).get("year"),
                    "authors": list(set(authors)),
                    "artists": list(set(artists))
                }
        except Exception as e:
            print(f"Error fetching from AniList: {e}")
        return None

    def fetch_mangabaka(self, search: str) -> Optional[Dict[str, Any]]:
        """
        Fetches metadata from MangaBaka API.
        Reference: https://api.mangabaka.dev/v1/
        """
        base_url = "https://api.mangabaka.dev/v1"
        try:
            # Search for the manga
            search_res = requests.get(f"{base_url}/search", params={"q": search, "type": "manga"}, timeout=10)
            if search_res.status_code == 200:
                results = search_res.json().get("results", [])
                if not results:
                    return None
                
                # Get the first match
                manga_data = results[0]
                return {
                    "source": "MangaBaka",
                    "title": manga_data.get("title") or manga_data.get("name"),
                    "synopsis": manga_data.get("synopsis") or manga_data.get("description"),
                    "genres": manga_data.get("genres", []),
                    "portada": manga_data.get("cover_url") or manga_data.get("image"),
                    "authors": manga_data.get("authors", []),
                    "artists": manga_data.get("artists", [])
                }
        except Exception as e:
            print(f"Error fetching from MangaBaka: {e}")
        return None

    def fetch_local(self, manga_id: str, root_path: str = ".") -> Optional[Dict[str, Any]]:
        """
        Reads existing metadata from a local folder if available.
        """
        path = Path(root_path) / f"_{manga_id}" / "inicio.md"
        if not path.exists():
            return None
        
        # Simple frontmatter parser
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
                import yaml
                parts = content.split("---")
                if len(parts) >= 3:
                    data = yaml.safe_load(parts[1])
                    return {
                        "source": "Local",
                        "title": data.get("title"),
                        "synopsis": data.get("sinopsis"),
                        "genres": data.get("generos", []),
                        "portada": data.get("portada"),
                        "authors": [data.get("autor")] if data.get("autor") else [],
                        "artists": [data.get("artista")] if data.get("artista") else []
                    }
        except Exception:
            pass
        return None

    def auto_fill(self, search: str, manga_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Tries all sources in order: AniList -> MangaBaka -> Local
        """
        result = self.fetch_anilist(search)
        if result: return result
        
        result = self.fetch_mangabaka(search)
        if result: return result
            
        if manga_id:
            result = self.fetch_local(manga_id)
            if result: return result
            
        return {}
