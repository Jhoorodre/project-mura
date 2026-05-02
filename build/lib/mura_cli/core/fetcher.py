import requests
from typing import Dict, Any, Optional

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
                media = response.json()["data"]["Media"]
                
                # Filter staff for authors and artists
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
                    "title": media["title"]["english"] or media["title"]["romaji"],
                    "synopsis": media.get("description", "").replace("<br>", "\n").replace("<i>", "").replace("</i>", ""),
                    "genres": media.get("genres", []),
                    "portada": media.get("coverImage", {}).get("extraLarge"),
                    "year": media.get("startDate", {}).get("year"),
                    "authors": list(set(authors)),
                    "artists": list(set(artists))
                }
        except Exception as e:
            print(f"Error fetching from AniList: {e}")
        return None

    def fetch_mangabaka(self, manga_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetches metadata from MangaBaka API.
        """
        # API logic based on: https://mangabaka.org/data/api
        # Assuming a simple GET request for now
        url = f"https://mangabaka.org/data/api/manga/{manga_id}"
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return {
                    "title": data.get("title"),
                    "synopsis": data.get("synopsis"),
                    "genres": data.get("genres", []),
                    "portada": data.get("cover"),
                    "authors": [data.get("author")] if data.get("author") else [],
                    # ... other fields
                }
        except Exception:
            pass
        return None
