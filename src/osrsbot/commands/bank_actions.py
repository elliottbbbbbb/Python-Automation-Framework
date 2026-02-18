"""
Bank Actions - CQRS Command layer for bank-related actions.

Handles:
- Opening bank (clicking banker)
- Searching and withdrawing items
- Depositing items
- All bank-related mouse interactions

Command layer responsibilities:
- WRITE operations (mutations)
- Execute actions based on query results
- Coordinate between queries and mouse service
"""

import logging
from typing import List, Optional, Union

import pyautogui

from osrsbot.queries.bank_queries import BankQueries
from osrsbot.services.mouse_service import MouseService
from osrsbot.utils.coordinate_helpers import CoordinateResolver
from osrsbot.utils.timing_helpers import TimingHelper

logger = logging.getLogger(__name__)


class BankActions:
    """Command layer for bank-related actions."""

    def __init__(
        self,
        mouse: MouseService,
        bank_queries: BankQueries,
        coord_resolver: CoordinateResolver,
        timing: TimingHelper,
    ):
        """
        Initialize bank actions.

        Args:
            mouse: Mouse service for clicking
            bank_queries: Bank queries for detecting elements
            coord_resolver: Coordinate resolution helper
            timing: Timing helper for waits
        """
        self.mouse = mouse
        self.bank_queries = bank_queries
        self.coord_resolver = coord_resolver
        self.timing = timing

    def is_bank_open(self, search_button_template: str) -> bool:
        """
        Check if bank interface is open.

        Delegates to query layer.

        Args:
            search_button_template: Path to bank search button template

        Returns:
            True if bank is open, False otherwise
        """
        return self.bank_queries.is_bank_open(search_button_template)

    def click_banker(
        self, banker_templates: List[str], threshold: float = 0.7
    ) -> bool:
        """
        Find and click banker using multiple templates.

        Args:
            banker_templates: List of paths to banker template images
            threshold: Match confidence threshold (0.0-1.0)

        Returns:
            True if banker found and clicked, False otherwise
        """
        # Query layer: find banker
        result = self.bank_queries.find_multi_template(banker_templates, threshold)

        if result is None:
            logger.warning(f"Banker not found (threshold: {threshold})")
            return False

        center_x, center_y, confidence, template_name = result

        logger.info(
            f"Found banker at ({center_x}, {center_y}) "
            f"with confidence {confidence:.3f} (template: {template_name})"
        )

        # Command layer: click banker
        abs_x, abs_y = self.coord_resolver.to_absolute(center_x, center_y)
        success = self.mouse.click_at(
            abs_x, abs_y, move_style="curved", speed_multiplier=1.0
        )

        if success:
            logger.info("Successfully clicked banker")
            return True
        else:
            logger.warning("Failed to click banker")
            return False

    def click_template(
        self, template_path: Union[str, List[str]], item_name: str, threshold: float = 0.7
    ) -> bool:
        """
        Find and click an item using template matching.

        Supports both single template and multiple templates for better accuracy
        across different zoom levels, camera angles, etc.

        Args:
            template_path: Path to template image (str) OR list of paths (List[str])
                          Single: "images/bot/items/overload.png"
                          Multiple: ["custom:overload_zoom1.png", "custom:overload_zoom2.png"]
            item_name: Name of item for logging
            threshold: Match confidence threshold (0.0-1.0)

        Returns:
            True if item found and clicked, False otherwise

        Examples:
            # Single template (fast, simple)
            click_template("images/bot/items/potion.png", "potion")

            # Multiple templates (better accuracy, slightly slower)
            click_template([
                "custom:potion_zoom1.png",
                "custom:potion_zoom2.png",
                "custom:potion_zoom3.png"
            ], "potion")
        """
        # Handle both single path (str) and multiple paths (list)
        if isinstance(template_path, str):
            # Single template - use find_template
            result = self.bank_queries.find_template(template_path, threshold)

            if result is None:
                logger.warning(f"{item_name} not found (threshold: {threshold})")
                return False

            center_x, center_y, confidence = result
            template_name = template_path

        elif isinstance(template_path, list):
            # Multiple templates - use find_multi_template
            result = self.bank_queries.find_multi_template(template_path, threshold)

            if result is None:
                logger.warning(f"{item_name} not found with any template (threshold: {threshold})")
                return False

            center_x, center_y, confidence, template_name = result

        else:
            logger.error(f"Invalid template_path type: {type(template_path)}")
            return False

        logger.info(
            f"Found {item_name} at ({center_x}, {center_y}) "
            f"with confidence {confidence:.3f}"
            + (f" (template: {template_name})" if isinstance(template_path, list) else "")
        )

        # Command layer: click item
        abs_x, abs_y = self.coord_resolver.to_absolute(center_x, center_y)
        success = self.mouse.click_at(
            abs_x, abs_y, move_style="curved", speed_multiplier=1.0
        )

        if success:
            logger.info(f"Successfully clicked {item_name}")
            return True
        else:
            logger.warning(f"Failed to click {item_name}")
            return False

    def search_and_withdraw(
        self,
        search_button_template: str,
        item_template: str,
        item_name: str,
        search_text: str,
        item_threshold: float = 0.7,
    ) -> bool:
        """
        Search for an item in bank and withdraw it.

        Clicks search button, types search text, clicks item, clears search.

        Args:
            search_button_template: Path to bank search button template
            item_template: Path to item template image
            item_name: Name of item for logging
            search_text: Text to type in search box
            item_threshold: Confidence threshold for item matching

        Returns:
            True if item found and withdrawn, False otherwise
        """
        try:
            # Click search button
            if not self.click_template(
                search_button_template, "bank search button", threshold=0.7
            ):
                logger.error("Failed to find bank search button")
                return False

            self.timing.wait("medium")

            # Type search text
            logger.info(f"Typing '{search_text}' in bank search")
            pyautogui.write(search_text, interval=0.05)
            self.timing.wait("long")  # Wait for search results to populate

            # Click item
            if not self.click_template(item_template, item_name, threshold=item_threshold):
                logger.error(f"Failed to find {item_name} in bank")
                # Clear search before returning
                pyautogui.press("escape")
                return False

            self.timing.wait("medium")

            # Clear search
            logger.debug("Clearing bank search")
            pyautogui.press("escape")
            self.timing.wait("medium")

            return True

        except Exception as e:
            logger.error(f"Error in bank search and withdraw: {e}")
            # Try to clear search on error
            try:
                pyautogui.press("escape")
            except Exception:
                pass
            return False
