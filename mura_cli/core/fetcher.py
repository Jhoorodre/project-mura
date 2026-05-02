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
              large
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
            response = requests.post(self.ANILIST_URL, json={'query': query, 'variables': variables})
            if response.status_code == 200:
                data = response.json()["data"]["Media"]
                # Simplify staff
                authors = [edge["node"]["name"]["full"] for edge in data["staff"]["edges"] if "Story" in edge["role"]]
                artists = [edge["node"]["name"]["full"] for edge in data["staff"]["edges"] if "Art" in edge["role"]]
                
                return {
                    "title": data["title"]["english"] or data["title"]["romaji"],
                    "synopsis": data["description"],
                    "genres": data["genres"],
                    "portada": data["coverImage"]["large"],
                    "year": data["startDate"]["year"],
                    "authors": authors,
                    "artists": artists
                }
        except Exception as e:
            print(f"Error fetching from AniList: {e}")
        return None

    def fetch_mangabaka(self, manga_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetches metadata from MangaBaka (Placeholder logic).
        """
        # Based on user-provided link: https://mangabaka.org/data/api
        # To be implemented when API details are confirmed
        return None
