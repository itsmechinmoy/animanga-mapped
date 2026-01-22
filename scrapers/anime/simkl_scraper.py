"""
SIMKL scraper using browse pages
File: scrapers/anime/simkl_scraper.py
"""
from typing import Dict, List, Any
import sys
from pathlib import Path
import os
from bs4 import BeautifulSoup
import re

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scrapers.base_scraper import BaseScraper

class SIMKLAnimeScraper(BaseScraper):
    """Scraper for SIMKL using web scraping of browse pages"""
    
    BASE_URL = "https://simkl.com"
    
    def __init__(self):
        super().__init__("simkl", "anime")
        
        # Add realistic browser headers
        self.session.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
        })
    
    def get_rate_limit(self) -> float:
        return 2.0  # 2 seconds between requests
    
    def scrape(self) -> List[Dict[str, Any]]:
        """Scrape SIMKL anime and movies from browse pages"""
        print("Scraping SIMKL browse pages...")
        print("Sources: /anime/ and /movies/\n")
        
        results = []
        
        # Scrape anime
        results.extend(self.scrape_category("anime"))
        
        # Scrape movies
        results.extend(self.scrape_category("movies"))
        
        # Deduplicate
        seen_ids = set()
        unique_results = []
        for item in results:
            simkl_id = item.get('id')
            if simkl_id and simkl_id not in seen_ids:
                seen_ids.add(simkl_id)
                unique_results.append(item)
        
        print(f"\n✓ Total unique items: {len(unique_results)}")
        return unique_results
    
    def scrape_category(self, category: str) -> List[Dict[str, Any]]:
        """Scrape a specific category (anime or movies)"""
        print(f"\nScraping /{category}/...")
        results = []
        
        page = self.checkpoint.get(f"{category}_page", 1)
        max_pages = 500  # Limit
        consecutive_errors = 0
        max_consecutive_errors = 5
        
        while page <= max_pages:
            try:
                url = f"{self.BASE_URL}/{category}/?page={page}"
                print(f"  Page {page}...")
                
                response = self.session.get(url)
                
                if response.status_code != 200:
                    print(f"    [!] HTTP {response.status_code}")
                    consecutive_errors += 1
                    if consecutive_errors >= max_consecutive_errors:
                        break
                    continue
                
                consecutive_errors = 0
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Find show items
                items = soup.select('.show, .poster, .item')
                
                if not items:
                    print(f"    No items found")
                    break
                
                for item in items:
                    try:
                        processed = self.process_item(item, category)
                        if processed:
                            results.append(processed)
                    except Exception as e:
                        continue
                
                print(f"    Found {len(items)} items")
                
                # Save checkpoint
                self.checkpoint[f"{category}_page"] = page + 1
                self.save_checkpoint(self.checkpoint)
                
                # Check for next page
                next_btn = soup.select_one('a.next, a[rel="next"]')
                if not next_btn:
                    print(f"    Reached last page")
                    break
                
                page += 1
                
            except Exception as e:
                print(f"    [ERROR] Page {page} failed: {e}")
                consecutive_errors += 1
                if consecutive_errors >= max_consecutive_errors:
                    break
        
        print(f"  Total from /{category}/: {len(results)}")
        return results
    
    def process_item(self, item: BeautifulSoup, category: str) -> Dict[str, Any]:
        """Process a SIMKL item"""
        # Try to find link
        link = item.select_one('a[href*="/anime/"], a[href*="/movies/"]')
        if not link:
            return None
        
        href = link.get('href', '')
        
        # Extract ID from URL
        # Format: /anime/123456/title or /movies/123456/title
        match = re.search(r'/(?:anime|movies)/(\d+)', href)
        if not match:
            return None
        
        simkl_id = match.group(1)
        
        # Get title
        title_elem = item.select_one('.title, h3, h4, .name')
        title = title_elem.get_text(strip=True) if title_elem else f"Unknown {simkl_id}"
        
        # Get type
        item_type = "MOVIE" if category == "movies" else "TV"
        
        # External IDs
        external_ids = {'simkl': simkl_id}
        
        # Metadata
        metadata = {
            "url": f"{self.BASE_URL}{href}",
            "category": category
        }
        
        return self.format_item(simkl_id, title, item_type, external_ids, metadata)
    
    def extract_external_ids(self, item: Dict[str, Any]) -> Dict[str, str]:
        """Extract external IDs"""
        return {}
