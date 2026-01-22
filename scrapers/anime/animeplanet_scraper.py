"""
Anime-Planet scraper (web scraping based)
File: scrapers/anime/animeplanet_scraper.py
NOTE: Anime-Planet blocks automated scraping. This scraper may not work.
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
        
        # Add more realistic headers to avoid being blocked
        self.session.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
    
    def get_rate_limit(self) -> float:
        return 3.0  # 3 seconds - be extra respectful
    
    def scrape(self) -> List[Dict[str, Any]]:
        """
        Scrape Anime-Planet data via web scraping
        WARNING: Anime-Planet actively blocks scrapers (403 Forbidden)
        This scraper will likely return 0 results
        """
        print("WARNING: Anime-Planet blocks automated scraping")
        print("This scraper may return 0 results due to 403 Forbidden errors")
        print("Attempting anyway with enhanced headers...\n")
        
        results = []
        page = self.checkpoint.get("page", 1)
        max_pages = 10  # Limit attempts
        consecutive_errors = 0
        max_consecutive_errors = 3
        
        while page <= max_pages:
            try:
                url = f"{self.BROWSE_URL}?page={page}"
                print(f"  Page {page}/{max_pages}...")
                
                response = self.session.get(url)
                
                if response.status_code == 403:
                    print(f"    [!] Access Forbidden (403) - Anime-Planet blocks scrapers")
                    print(f"    [!] Stopping scrape. Use AniDB/AniList instead for anime-planet slugs")
                    break
                
                if response.status_code != 200:
                    print(f"    [!] HTTP {response.status_code}")
                    consecutive_errors += 1
                    if consecutive_errors >= max_consecutive_errors:
                        break
                    continue
                
                consecutive_errors = 0
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Find anime cards
                cards = soup.select('li.card')
                
                if not cards:
                    print("    No items found")
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
                consecutive_errors += 1
                if consecutive_errors >= max_consecutive_errors:
                    break
        
        if not results:
            print("\n[!] No results - Anime-Planet blocks scrapers")
            print("[!] Consider using other services for anime-planet IDs")
        
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
