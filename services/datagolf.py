"""DataGolf API client."""
import httpx
from config import DATAGOLF_API_KEY


class DataGolfClient:
    """Client for DataGolf API."""

    BASE_URL = "https://feeds.datagolf.com"

    def __init__(self, api_key: str = None):
        self.api_key = api_key or DATAGOLF_API_KEY
        self._client = httpx.Client(timeout=30.0)

    def _get(self, endpoint: str, params: dict = None) -> dict:
        """Make authenticated GET request."""
        params = params or {}
        params["key"] = self.api_key
        response = self._client.get(f"{self.BASE_URL}/{endpoint}", params=params)
        response.raise_for_status()
        return response.json()

    def get_schedule(self, tour: str = "pga") -> list:
        """Get tour schedule."""
        data = self._get("get-schedule", {"tour": tour})
        return data.get("schedule", [])

    def get_field_updates(self, tour: str = "pga") -> dict:
        """Get current tournament field with tee times, WDs, etc."""
        return self._get("field-updates", {"tour": tour})

    def get_player_list(self) -> list:
        """Get all players with DataGolf IDs."""
        return self._get("get-player-list")

    def get_rankings(self) -> list:
        """Get DG rankings with skill estimates."""
        data = self._get("preds/get-dg-rankings")
        return data.get("rankings", [])

    def get_live_stats(self, tour: str = "pga") -> dict:
        """Get live tournament scoring and stats."""
        return self._get("preds/live-tournament-stats", {"tour": tour})

    def get_live_predictions(self, tour: str = "pga") -> dict:
        """Get in-play predictions."""
        return self._get("preds/in-play", {"tour": tour})
