"""
Anime-Planet scraper (web scraping based)
File: scrapers/anime/animeplanet_scraper.py
"""
from typing import Dict, List, Any
import sys
from pathlib import Path
from bs4 import BeautifulSoup
import re

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scrapers.base_scraper import BaseScraper

class AnimePlanetScraper(BaseScraper):
    """Scraper for Anime-Planet (web scraping)"""
    
    BASE_URL = "https://www.anime-planet.com"
    BROWSE_URL = f"{BASE_URL}/anime/all"
    
    def __init__(self):
        super().__init__("animeplanet", "anime")
    
    def get_rate_limit(self) -> float:
        return 2.0  # 2 seconds - be respectful with web scraping
    
    def scrape(self) -> List[Dict[str, Any]]:
        """
        Scrape Anime-Planet data via web scraping
        Note: This is a simplified implementation
        A full implementation would require more sophisticated pagination
        """
        print("Scraping Anime-Planet via web scraping...")
        print("Note: This may take a while and is limited by pagination\n")
        
        results = []
        page = self.checkpoint.get("page", 1)
        max_pages = 500  # Limit to avoid excessive requests
        
        while page <= max_pages:
            try:
                url = f"{self.BROWSE_URL}?page={page}"
                print(f"  Page {page}/{max_pages}...")
                
                response = self.session.get(url)
                
                if response.status_code != 200:
                    print(f"    [!] HTTP {response.status_code}")
                    break
                
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Find anime cards
                cards = soup.select('li.card')
                
                if not cards:
                    print("    No more items found")
                    break
                
                for card in cards:
                    try:
                        processed = self.process_card(card)
                        if processed:
                            results.append(processed)
                    except Exception as e:
                        continue
                
                print(f"    Found {len(cards)} items")
                
                # Save checkpoint
                self.checkpoint['page'] = page + 1
                self.save_checkpoint(self.checkpoint)
                
                page += 1
                
                # Check if there's a next page
                next_link = soup.select_one('a.next')
                if not next_link:
                    print("\n  Reached last page")
                    break
                
            except Exception as e:
                print(f"    [ERROR] Page {page} failed: {e}")
                break
        
        print(f"\n✓ Processed {len(results)} items")
        return results
    
    def process_card(self, card: BeautifulSoup) -> Dict[str, Any]:
        """Process an anime card element"""
        # Get link and slug
        link = card.select_one('a[href*="/anime/"]')
        if not link:
            return None
        
        href = link.get('href', '')
        # Extract slug from URL like /anime/slug-name
        match = re.search(r'/anime/([^/?]+)', href)
        if not match:
            return None
        
        slug = match.group(1)
        
        # Get title
        title_elem = card.select_one('h3, h4, .cardName')
        title = title_elem.get_text(strip=True) if title_elem else slug
        
        # Get type
        type_elem = card.select_one('.type')
        item_type = type_elem.get_text(strip=True) if type_elem else ""
        
        # Get year
        year_elem = card.select_one('.year')
        year = year_elem.get_text(strip=True) if year_elem else None
        
        # External IDs (slug is the ID for Anime-Planet)
        external_ids = {'animeplanet': slug}
        
        # Metadata
        metadata = {
            "slug": slug,
            "url": f"{self.BASE_URL}{href}",
            "type": item_type,
            "year": year
        }
        
        return self.format_item(slug, title, item_type, external_ids, metadata)
    
    def extract_external_ids(self, item: Dict[str, Any]) -> Dict[str, str]:
        """Anime-Planet uses slugs as IDs"""
        return {'animeplanet': item.get('slug', '')}
