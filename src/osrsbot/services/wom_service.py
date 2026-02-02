"""
Wise Old Man API client for looking up OSRS player stats.

API docs: https://docs.wiseoldman.net
Rate limit: 20 requests per 60 seconds (no API key).
"""

import logging

import requests

logger = logging.getLogger(__name__)

WOM_BASE = "https://api.wiseoldman.net/v2"


def get_skill_level(rsn: str, skill: str) -> int | None:
    """
    Fetch a player's level for a given skill from the Wise Old Man API.

    Args:
        rsn: RuneScape display name.
        skill: Skill name (lowercase), e.g. "fletching", "cooking".

    Returns:
        The player's level as an int, or None if lookup failed.
    """
    try:
        resp = requests.get(
            f"{WOM_BASE}/players/{rsn}",
            headers={"User-Agent": "OSRSAutomationFramework"},
            timeout=10,
        )
        if resp.status_code == 404:
            logger.warning(f"WOM: Player '{rsn}' not found")
            return None
        resp.raise_for_status()

        data = resp.json()
        snapshot = data.get("latestSnapshot")
        if not snapshot:
            logger.warning(f"WOM: No snapshot data for '{rsn}'")
            return None

        skills = snapshot["data"]["skills"]
        skill_data = skills.get(skill)
        if not skill_data:
            logger.warning(f"WOM: Skill '{skill}' not found in response")
            return None

        level = skill_data["level"]
        logger.info(f"WOM: {rsn} has {skill} level {level}")
        return level

    except requests.RequestException as e:
        logger.warning(f"WOM: API request failed - {e}")
        return None
    except (KeyError, TypeError) as e:
        logger.warning(f"WOM: Failed to parse response - {e}")
        return None
