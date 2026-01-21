"""
Livechart scraper (web scraping based)
File: scrapers/anime/livechart_scraper.py
"""
from typing import Dict, List, Any
import sys
from pathlib import Path
from bs4 import BeautifulSoup
import re
import time

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scrapers.base_scraper import BaseScraper

class LivechartScraper(BaseScraper):
    """Scraper for Livechart.me (web scraping)"""
    
    BASE_URL = "https://www.livechart.me"
    
    def __init__(self):
        super().__init__("livechart", "anime")
    
    def get_rate_limit(self) -> float:
        return 2.0  # 2 seconds between requests
    
    def scrape(self) -> List[Dict[str, Any]]:
        """
        Scrape Livechart data
        Livechart organizes anime by season, so we'll scrape multiple seasons
        """
        print("Scraping Livechart by season...")
        print("Note: This covers 2020-2026 seasons\n")
        
        results = []
        
        # Generate seasons (year + season)
        years = range(2020, 2027)
        seasons_list = ['winter', 'spring', 'summer', 'fall']
        
        start_year = self.checkpoint.get("year", 2020)
        start_season = self.checkpoint.get("season", 'winter')
        
        started = False
        
        for year in years:
            for season in seasons_list:
                # Skip until we reach checkpoint
                if not started:
                    if year == start_year and season == start_season:
                        started = True
                    else:
                        continue
                
                try:
                    print(f"  {season.capitalize()} {year}...")
                    
                    url = f"{self.BASE_URL}/{season}-{year}/tv"
                    response = self.session.get(url)
                    
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.content, 'html.parser')
                        
                        # Find anime items
                        items = soup.select('.anime-card, article.anime')
                        
                        for item in items:
                            try:
                                processed = self.process_item(item)
                                if processed:
                                    results.append(processed)
                            except Exception as e:
                                continue
                        
                        print(f"    Found {len(items)} items")
                    
                    # Save checkpoint
                    self.checkpoint['year'] = year
                    self.checkpoint['season'] = season
                    self.save_checkpoint(self.checkpoint)
                    
                    time.sleep(1)  # Extra delay between seasons
                    
                except Exception as e:
                    print(f"    [WARN] {season} {year} failed: {e}")
                    continue
        
        print(f"\n✓ Processed {len(results)} items")
        return results
    
    def process_item(self, item: BeautifulSoup) -> Dict[str, Any]:
        """Process a Livechart anime item"""
        # Get link to anime page
        link = item.select_one('a[href*="/anime/"]')
        if not link:
            return None
        
        href = link.get('href', '')
        
        # Extract ID from URL like /anime/12345
        match = re.search(r'/anime/(\d+)', href)
        if not match:
            return None
        
        livechart_id = match.group(1)
        
        # Get title
        title_elem = item.select_one('h3, .anime-card__title, .main-title')
        title = title_elem.get_text(strip=True) if title_elem else f"Unknown {livechart_id}"
        
        # Get type
        type_elem = item.select_one('.anime-card__type, .anime-type')
        item_type = type_elem.get_text(strip=True) if type_elem else ""
        
        # External IDs
        external_ids = {'livechart': livechart_id}
        
        # Try to extract MAL link if available
        mal_link = item.select_one('a[href*="myanimelist.net"]')
        if mal_link:
            mal_href = mal_link.get('href', '')
            mal_match = re.search(r'/anime/(\d+)', mal_href)
            if mal_match:
                external_ids['mal'] = mal_match.group(1)
        
        # Try to extract AniList link
        anilist_link = item.select_one('a[href*="anilist.co"]')
        if anilist_link:
            al_href = anilist_link.get('href', '')
            al_match = re.search(r'/anime/(\d+)', al_href)
            if al_match:
                external_ids['anilist'] = al_match.group(1)
        
        # Metadata
        metadata = {
            "url": f"{self.BASE_URL}{href}",
            "type": item_type
        }
        
        return self.format_item(livechart_id, title, item_type, external_ids, metadata)
    
    def extract_external_ids(self, item: Dict[str, Any]) -> Dict[str, str]:
        """Extract external IDs"""
        # Already done in process_item
        return {}
