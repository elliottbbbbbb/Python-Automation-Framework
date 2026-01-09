"""
Zulrah Combat Management System

Handles all combat-related actions:
- Prayer switching
- Gear switching
- Attacking Zulrah/Snakelings
- HP/Prayer monitoring
- Food/Potion consumption
"""

import logging
from typing import Tuple

logger = logging.getLogger(__name__)


class ZulrahCombatManager:
    """Manages combat actions during Zulrah fight."""

    def __init__(self, actions, queries, screen_service, config):
        """
        Initialize combat manager.

        Args:
            actions: GameActions/CombatActions for performing actions
            queries: GameState/StatQueries for reading state
            screen_service: ScreenService for color detection
            config: Config object
        """
        self.actions = actions
        self.queries = queries
        self.screen = screen_service
        self.config = config

        # Get config values
        zulrah_config = config.get("zulrah", {})
        self.hp_threshold = zulrah_config.get("hp_threshold", 40)
        self.prayer_threshold = zulrah_config.get("prayer_threshold", 20)
        self.food_slot = zulrah_config.get("food_slot", 1)
        self.prayer_potion_slot = zulrah_config.get("prayer_potion_slot", 2)

    def switch_prayer(self, prayer: str) -> bool:
        """
        Switch to appropriate prayer.

        Args:
            prayer: Prayer name - 'protect_magic', 'protect_ranged',
                   'protect_melee', or 'protect_both'

        Returns:
            True if prayer switched successfully, False otherwise
        """
        try:
            # Record action for anti-ban pattern detection
            if hasattr(self.actions, 'anti_ban') and self.actions.anti_ban:
                self.actions.anti_ban.record_action(f"prayer_{prayer}")

            # Handle jad phase (protect_both means pray ranged usually)
            if prayer == "protect_both":
                prayer = "protect_ranged"  # Safest default for jad phase

            logger.info(f"Switching to: {prayer}")

            # Use existing CombatActions methods
            if prayer == "protect_magic":
                success = self.actions.activate_protect_from_magic()
            elif prayer == "protect_ranged":
                success = self.actions.activate_protect_from_ranged()
            elif prayer == "protect_melee":
                success = self.actions.activate_protect_from_melee()
            else:
                logger.error(f"Unknown prayer: {prayer}")
                return False

            # Small variance wait after prayer switch (human reaction time)
            if success:
                self.actions.wait("short")

            return success

        except Exception as e:
            logger.error(f"Error switching prayer: {e}")
            return False

    def switch_gear(self, attack_style: str) -> bool:
        """
        Switch gear for appropriate attack style.

        Args:
            attack_style: 'mage', 'range', or 'both'

        Returns:
            True if gear switched, False otherwise
        """
        try:
            # Record action for anti-ban pattern detection
            if hasattr(self.actions, 'anti_ban') and self.actions.anti_ban:
                self.actions.anti_ban.record_action(f"gear_{attack_style}")

            # For 'both', just keep current gear
            if attack_style == "both":
                logger.debug("Jad phase - no gear switch needed")
                return True

            # Simplified gear switching - assumes gear is in specific slots
            # Slot 20 = mage weapon, Slot 21 = range weapon (example)
            if attack_style == "mage":
                logger.debug("Switching to mage gear")
                # Click mage weapon slot
                self.actions.click_inventory_slot(20)
                self.actions.wait("short")
                return True

            elif attack_style == "range":
                logger.debug("Switching to range gear")
                # Click range weapon slot
                self.actions.click_inventory_slot(21)
                self.actions.wait("short")
                return True

            else:
                logger.warning(f"Unknown attack style: {attack_style}")
                return False

        except Exception as e:
            logger.error(f"Error switching gear: {e}")
            return False

    def attack_zulrah(self) -> bool:
        """
        Click on Zulrah to attack using color detection.

        Tries to detect and click on any visible Zulrah form
        (serpentine, tanzanite, or magma).

        Returns:
            True if Zulrah found and clicked, False otherwise
        """
        try:
            # Get form colors from config
            form_colors = self.config.get("zulrah", {}).get("form_colors", {})
            tolerance = self.config.get("zulrah", {}).get("color_tolerance", 30)

            # Try to find and click each Zulrah form color
            for form_name, hex_color in form_colors.items():
                # Use screen service to find the color
                match = self.screen.find_color(hex_color, tolerance=tolerance)

                if match:
                    # Record action for anti-ban pattern detection
                    if hasattr(self.actions, 'anti_ban') and self.actions.anti_ban:
                        self.actions.anti_ban.record_action(f"attack_zulrah_{form_name}")

                    # Found Zulrah - click it
                    logger.debug(f"Found Zulrah ({form_name}) at ({match.x}, {match.y})")
                    self.actions.mouse.move_to(match.x, match.y, move_style="curved")
                    self.actions.mouse.click()
                    logger.info(f"Attacked Zulrah ({form_name})")
                    return True

            logger.warning("Could not find Zulrah to attack (not visible)")
            return False

        except Exception as e:
            logger.error(f"Error attacking Zulrah: {e}")
            return False

    def attack_snakeling(self, position: Tuple[int, int]) -> bool:
        """
        Click on snakeling at given position.

        Args:
            position: (x, y) screen coordinates of snakeling

        Returns:
            True if click attempted, False on error
        """
        try:
            # Record action for anti-ban pattern detection
            if hasattr(self.actions, 'anti_ban') and self.actions.anti_ban:
                self.actions.anti_ban.record_action("attack_snakeling")

            x, y = position
            logger.info(f"Attacking snakeling at ({x}, {y})")

            self.actions.mouse.move_to(x, y, move_style="curved")
            self.actions.mouse.click()

            # Small wait after attacking
            self.actions.wait("short")

            return True

        except Exception as e:
            logger.error(f"Error attacking snakeling: {e}")
            return False

    def check_needs_food(self) -> bool:
        """
        Check if HP is below threshold.

        Returns:
            True if we should eat, False otherwise
        """
        try:
            hp = self.queries.get_hp()

            if hp is None:
                logger.warning("Could not read HP")
                return False

            needs_food = hp < self.hp_threshold
            if needs_food:
                logger.info(f"HP {hp} below threshold {self.hp_threshold}")

            return needs_food

        except Exception as e:
            logger.error(f"Error checking HP: {e}")
            return False

    def eat_food(self) -> bool:
        """
        Eat food from configured inventory slot.

        Returns:
            True if food consumed, False otherwise
        """
        try:
            # Record action for anti-ban pattern detection
            if hasattr(self.actions, 'anti_ban') and self.actions.anti_ban:
                self.actions.anti_ban.record_action("eat_food")

            logger.info(f"Eating food from slot {self.food_slot}")
            success = self.actions.click_inventory_slot(self.food_slot)

            # Small wait after eating (human reaction time)
            if success:
                self.actions.wait("short")

            return success

        except Exception as e:
            logger.error(f"Error eating food: {e}")
            return False

    def check_needs_prayer_potion(self) -> bool:
        """
        Check if prayer is below threshold.

        Returns:
            True if we should drink prayer potion, False otherwise
        """
        try:
            prayer = self.queries.get_prayer()

            if prayer is None:
                logger.warning("Could not read prayer")
                return False

            needs_prayer = prayer < self.prayer_threshold
            if needs_prayer:
                logger.info(f"Prayer {prayer} below threshold {self.prayer_threshold}")

            return needs_prayer

        except Exception as e:
            logger.error(f"Error checking prayer: {e}")
            return False

    def drink_prayer_potion(self) -> bool:
        """
        Drink prayer potion from configured slot.

        Returns:
            True if potion consumed, False otherwise
        """
        try:
            # Record action for anti-ban pattern detection
            if hasattr(self.actions, 'anti_ban') and self.actions.anti_ban:
                self.actions.anti_ban.record_action("drink_prayer_potion")

            logger.info(f"Drinking prayer potion from slot {self.prayer_potion_slot}")
            success = self.actions.click_inventory_slot(self.prayer_potion_slot)

            # Small wait after drinking (human reaction time)
            if success:
                self.actions.wait("short")

            return success

        except Exception as e:
            logger.error(f"Error drinking prayer potion: {e}")
            return False

    def check_has_food(self) -> bool:
        """
        Check if we have food available.

        Simple check - assumes slot contains food if not empty.

        Returns:
            True if food available, False otherwise
        """
        try:
            # Check if food slot is not empty
            # This is simplified - ideally would detect actual food
            empty_color = self.config.get("colors", {}).get("empty_inventory_slot")
            if not empty_color:
                return True  # Assume we have food if can't check

            # Get slot position and check color
            # Simplified implementation
            return True  # For now, assume we have food

        except Exception as e:
            logger.error(f"Error checking food: {e}")
            return True  # Assume we have food on error
