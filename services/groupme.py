"""GroupMe API client for bot messaging and member verification."""
import httpx
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class GroupMeClient:
    """Client for GroupMe API."""

    BASE_URL = "https://api.groupme.com/v3"
    TIMEOUT = 10.0

    def __init__(self, bot_id: str = None, db_module=None):
        """Initialize GroupMe client.

        Args:
            bot_id: GroupMe bot ID for sending messages (direct)
            db_module: Database module to check app_settings for bot_id (optional, takes priority)
        """
        # Check app_settings first if db_module provided
        if db_module:
            try:
                for setting in db_module.app_settings():
                    if setting.key == 'groupme_bot_id':
                        bot_id = setting.value
                        break
            except Exception as e:
                logger.warning(f"Failed to fetch bot_id from app_settings: {e}")

        # Fall back to provided bot_id or env var
        if not bot_id:
            from config import GROUPME_BOT_ID
            bot_id = GROUPME_BOT_ID

        self.bot_id = bot_id

    def send_message(self, text: str) -> bool:
        """Send message via GroupMe bot.

        Args:
            text: Message text to send

        Returns:
            True if sent successfully, False on error
        """
        if not self.bot_id:
            logger.warning("GroupMe bot_id not configured, skipping message send")
            return False

        try:
            url = f"{self.BASE_URL}/bots/post"
            payload = {"text": text, "bot_id": self.bot_id}
            with httpx.Client(timeout=self.TIMEOUT) as client:
                response = client.post(url, json=payload)
                response.raise_for_status()
            logger.info(f"GroupMe message sent: {text[:50]}...")
            return True
        except Exception as e:
            logger.error(f"Failed to send GroupMe message: {e}")
            return False

    def verify_member(self, groupme_name: str, group_id: str, access_token: str) -> bool:
        """Verify if a user is a member of the group.

        Args:
            groupme_name: User's GroupMe display name
            group_id: GroupMe group ID
            access_token: GroupMe API access token

        Returns:
            True if member found, False otherwise
        """
        if not access_token or not group_id:
            logger.warning("GroupMe access_token or group_id not configured, skipping verification")
            return True  # Allow registration to proceed

        try:
            url = f"{self.BASE_URL}/groups/{group_id}"
            headers = {"X-Access-Token": access_token}
            with httpx.Client(timeout=self.TIMEOUT) as client:
                response = client.get(url, headers=headers)
                response.raise_for_status()
                data = response.json()

            members = data.get("response", {}).get("members", [])

            # Check if groupme_name matches any member's nickname
            for member in members:
                member_nickname = member.get("nickname", "").strip().lower()
                input_name = groupme_name.strip().lower()
                if member_nickname == input_name:
                    logger.info(f"GroupMe member verified: {groupme_name}")
                    return True

            logger.warning(f"GroupMe member not found: {groupme_name}")
            return False
        except Exception as e:
            logger.error(f"Failed to verify GroupMe member: {e}")
            return False  # Block registration on verification failure
