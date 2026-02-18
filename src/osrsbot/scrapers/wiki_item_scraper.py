"""
WikiItemScraper - Download OSRS item images from oldschool.runescape.wiki.

Scrapes item inventory icons from the OSRS Wiki using the MediaWiki API.
Saves images to auto/ directory for use by ItemDetectionService.

Usage:
    scraper = WikiItemScraper()
    success = scraper.scrape_item(385, "Shark")
    batch_results = scraper.scrape_batch([(385, "Shark"), (386, "Lobster")])
"""

import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests
from PIL import Image

logger = logging.getLogger(__name__)


class WikiItemScraper:
    """
    Scraper for downloading OSRS item inventory icons from the wiki.

    Uses MediaWiki API to find and download item images.
    Resizes to standard inventory icon size (36×32).
    Saves to auto/ directory with format: {item_id}_{item_name}.png
    """

    def __init__(self, output_dir: str = "images/items/auto"):
        """
        Initialize WikiItemScraper.

        Args:
            output_dir: Directory to save downloaded images (auto/ directory)
        """
        output_path = Path(output_dir)
        if not output_path.is_absolute():
            package_root = Path(__file__).resolve().parent.parent
            output_path = package_root / output_dir
        self.output_dir = output_path
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.base_url = "https://oldschool.runescape.wiki"
        self.api_url = f"{self.base_url}/api.php"

        # Standard OSRS inventory icon size
        self.target_width = 36
        self.target_height = 32

        logger.info(f"WikiItemScraper initialized, output: {self.output_dir}")

    def scrape_item(self, item_id: int, item_name: str) -> bool:
        """
        Scrape single item icon from wiki.

        Process:
        1. Query MediaWiki API for File:{ItemName}_detail.png
        2. Fallback to File:{ItemName}.png if not found
        3. Download image
        4. Resize to 36×32 (OSRS inventory icon size)
        5. Save as {item_id}_{item_name}.png

        Args:
            item_id: OSRS item ID
            item_name: Item name (e.g., "Shark", "Lobster")

        Returns:
            True if successful, False otherwise
        """
        # Normalize item name for filename (lowercase, underscores)
        item_name_normalized = item_name.lower().replace(" ", "_")
        output_file = self.output_dir / f"{item_id}_{item_name_normalized}.png"

        # Skip if already exists
        if output_file.exists():
            logger.info(f"Item {item_name} already exists, skipping")
            return True

        try:
            # Try to find image URL from wiki
            image_url = self._find_image_url(item_name)

            if not image_url:
                logger.warning(f"Could not find image for {item_name}")
                return False

            # Download image
            logger.info(f"Downloading {item_name} from {image_url}")
            image = self._download_image(image_url)

            if image is None:
                logger.warning(f"Failed to download image for {item_name}")
                return False

            # Resize to standard inventory icon size
            image_resized = self._resize_image(image, self.target_width, self.target_height)

            # Save image
            image_resized.save(output_file)
            logger.info(f"Saved {item_name} to {output_file}")

            return True

        except Exception as e:
            logger.error(f"Error scraping {item_name}: {e}")
            return False

    def scrape_batch(
        self, item_list: List[Tuple[int, str]], rate_limit: float = 1.0
    ) -> Dict[str, bool]:
        """
        Scrape multiple items in batch with rate limiting.

        Args:
            item_list: List of (item_id, item_name) tuples
            rate_limit: Delay between requests in seconds (default 1.0)

        Returns:
            Dict mapping item_name → success status
        """
        results = {}

        for i, (item_id, item_name) in enumerate(item_list):
            logger.info(f"Scraping {i+1}/{len(item_list)}: {item_name}")

            success = self.scrape_item(item_id, item_name)
            results[item_name] = success

            # Rate limiting (be respectful to wiki)
            if i < len(item_list) - 1:  # Don't delay after last item
                time.sleep(rate_limit)

        # Summary
        successful = sum(1 for v in results.values() if v)
        logger.info(f"Batch scraping complete: {successful}/{len(item_list)} successful")

        return results

    def _find_image_url(self, item_name: str) -> Optional[str]:
        """
        Find image URL for item using MediaWiki API.

        Tries multiple filename variants:
        1. {ItemName}_detail.png (inventory icon with detail)
        2. {ItemName}.png (standard inventory icon)

        Args:
            item_name: Item name

        Returns:
            Image URL if found, None otherwise
        """
        # Try different filename variants
        filename_variants = [
            f"{item_name}_detail.png",
            f"{item_name}.png",
            f"{item_name}_inventory.png",
        ]

        for filename in filename_variants:
            try:
                # Query MediaWiki API
                params = {
                    "action": "query",
                    "titles": f"File:{filename}",
                    "prop": "imageinfo",
                    "iiprop": "url",
                    "format": "json",
                }

                response = requests.get(self.api_url, params=params, timeout=10)
                response.raise_for_status()

                data = response.json()

                # Extract image URL
                pages = data.get("query", {}).get("pages", {})
                for page_id, page_data in pages.items():
                    if page_id == "-1":  # Page not found
                        continue

                    imageinfo = page_data.get("imageinfo", [])
                    if imageinfo:
                        url = imageinfo[0].get("url")
                        if url:
                            logger.debug(f"Found image URL for {item_name}: {url}")
                            return url

            except Exception as e:
                logger.debug(f"Error querying filename {filename}: {e}")
                continue

        return None

    def _download_image(self, url: str) -> Optional[Image.Image]:
        """
        Download image from URL.

        Args:
            url: Image URL

        Returns:
            PIL Image if successful, None otherwise
        """
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            from io import BytesIO

            image = Image.open(BytesIO(response.content))
            return image

        except Exception as e:
            logger.error(f"Error downloading image from {url}: {e}")
            return None

    def _resize_image(self, image: Image.Image, target_width: int, target_height: int) -> Image.Image:
        """
        Resize image to target dimensions while maintaining aspect ratio.

        Args:
            image: PIL Image
            target_width: Target width in pixels
            target_height: Target height in pixels

        Returns:
            Resized PIL Image
        """
        # Convert to RGB if needed (remove alpha channel)
        if image.mode == "RGBA":
            # Create white background
            background = Image.new("RGB", image.size, (255, 255, 255))
            background.paste(image, mask=image.split()[3])  # Use alpha channel as mask
            image = background
        elif image.mode != "RGB":
            image = image.convert("RGB")

        # Resize maintaining aspect ratio (fit within target size)
        image.thumbnail((target_width, target_height), Image.Resampling.LANCZOS)

        # Create new image with target size (pad if needed)
        result = Image.new("RGB", (target_width, target_height), (255, 255, 255))

        # Center the resized image
        paste_x = (target_width - image.width) // 2
        paste_y = (target_height - image.height) // 2
        result.paste(image, (paste_x, paste_y))

        return result

    def update_database(
        self,
        items_db_path: str = "src/osrsbot/data/items_database.json",
        item_id: int = None,
        item_name: str = None,
    ) -> None:
        """
        Update items database with newly scraped item.

        Args:
            items_db_path: Path to items database JSON
            item_id: Item ID to add
            item_name: Item name to add
        """
        db_path = Path(items_db_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)

        # Load existing database
        if db_path.exists():
            with open(db_path, "r") as f:
                database = json.load(f)
        else:
            database = {}

        # Add new item
        if item_id and item_name:
            item_name_normalized = item_name.lower().replace(" ", "_")
            database[str(item_id)] = {
                "name": item_name,
                "filename": f"{item_id}_{item_name_normalized}.png",
                "source": "wiki",
                "scraped_at": datetime.now().isoformat(),
                "override": False,
            }

        # Save database
        with open(db_path, "w") as f:
            json.dump(database, f, indent=2)

        logger.info(f"Updated items database: {db_path}")
