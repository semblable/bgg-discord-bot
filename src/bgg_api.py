import requests
from xml.etree import ElementTree
from typing import Optional, Dict, List

BGG_API_BASE = "https://boardgamegeek.com/xmlapi2/"


class BGGClient:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "DiscordBGGBot/1.0"})

    def _make_request(
        self, endpoint: str, params: Optional[Dict] = None
    ) -> ElementTree.Element:
        """Make a request to the BGG API and return parsed XML"""
        try:
            response = self.session.get(f"{BGG_API_BASE}{endpoint}", params=params)
            response.raise_for_status()
            return ElementTree.fromstring(response.content)
        except requests.exceptions.RequestException as e:
            raise Exception(f"BGG API request failed: {str(e)}")

    def search_bgg(
        self, query: str, game_types: str = "boardgame,boardgameexpansion"
    ) -> List[Dict]:
        """Search for games on BGG"""
        params = {"query": query, "type": game_types}
        root = self._make_request("search", params)

        return [
            {
                "id": item.get("id"),
                "name": item.find("name").get("value"),
                "year": (
                    item.find("yearpublished").get("value")
                    if item.find("yearpublished") is not None
                    else None
                ),
            }
            for item in root.findall("item")
        ]

    def fetch_thing_data(self, item_id: str, stats: bool = False) -> Dict:
        """Fetch detailed information about a specific game"""
        params = {"id": item_id, "stats": 1 if stats else 0}
        root = self._make_request("thing", params)

        item = root.find("item")
        if item is None:
            raise Exception("No game found with that ID")

        return self._parse_thing_data(item)

    def _parse_thing_data(self, item: ElementTree.Element) -> Dict:
        """Parse detailed game information from XML"""
        result = {
            "id": item.get("id"),
            "type": item.get("type"),
            "name": item.find("name").get("value"),
            "year": item.find("yearpublished").get("value"),
            "image": (
                item.find("image").text if item.find("image") is not None else None
            ),
            "description": (
                item.find("description").text
                if item.find("description") is not None
                else None
            ),
        }

        if item.find("statistics") is not None:
            ratings = item.find("statistics/ratings")
            result["stats"] = {
                "average": ratings.find("average").get("value"),
                "weight": ratings.find("averageweight").get("value"),
                "users_rated": ratings.find("usersrated").get("value"),
                "ranks": [
                    {
                        "type": rank.get("type"),
                        "id": rank.get("id"),
                        "name": rank.get("name"),
                        "value": rank.get("value"),
                    }
                    for rank in ratings.findall("ranks/rank")
                ],
            }

        return result

    def fetch_hot_items(self, item_type: str = "boardgame") -> List[Dict]:
        """Get the current hot items list from BGG"""
        params = {"type": item_type}
        root = self._make_request("hot", params)

        return [
            {
                "id": item.get("id"),
                "rank": item.get("rank"),
                "name": item.find("name").get("value"),
                "year": (
                    item.find("yearpublished").get("value")
                    if item.find("yearpublished") is not None
                    else None
                ),
            }
            for item in root.findall("item")
        ]
