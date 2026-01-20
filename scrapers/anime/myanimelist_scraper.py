"""
MyAnimeList scraper using Jikan API v4
"""
from typing import Dict, List, Any
from scrapers.base_scraper import BaseScraper
import re

class MyAnimeListScraper(BaseScraper):
    """Scraper for MyAnimeList via Jikan API"""
    
    API_URL = "https://api.jikan.moe/v4/anime"
    
    def __init__(self):
        super().__init__("myanimelist", "anime")
    
    def get_rate_limit(self) -> float:
        return 1.0  # Jikan has strict rate limits
    
    def scrape(self) -> List[Dict[str, Any]]:
        """Scrape MAL data via Jikan"""
        results = []
        page = self.checkpoint.get("page", 1)
        
        print(f"Starting from page {page}...")
        
        while True:
            try:
                response = self.session.get(
                    f"{self.API_URL}?page={page}&limit=25"
                )
                
                if response.status_code == 429:
                    print("  Rate limited. Waiting 60s...")
                    import time
                    time.sleep(60)
                    continue
                
                data = response.json()
                
                if 'data' not in data or not data['data']:
                    break
                
                items = data['data']
                pagination = data.get('pagination', {})
                
                print(f"  Page {page}/{pagination.get('last_visible_page', '?')} - {len(items)} items")
                
                for item in items:
                    mal_id = item['mal_id']
                    
                    # Get full details
                    try:
                        detail_response = self.session.get(f"{self.API_URL}/{mal_id}/full")
                        full_data = detail_response.json().get('data', item)
                    except:
                        full_data = item
                    
                    processed = self.process_item(full_data)
                    results.append(processed)
                
                # Save checkpoint
                self.checkpoint['page'] = page + 1
                self.save_checkpoint(self.checkpoint)
                
                if not pagination.get('has_next_page'):
                    break
                
                page += 1
                
            except Exception as e:
                print(f"  [ERROR] Page {page} failed: {e}")
                break
        
        return results
    
    def process_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single MAL item"""
        mal_id = item['mal_id']
        title = item.get('title', '')
        item_type = item.get('type', '')
        
        external_ids = self.extract_external_ids(item)
        
        metadata = {
            "titles": {
                "english": item.get('title_english'),
                "japanese": item.get('title_japanese'),
                "synonyms": item.get('title_synonyms', [])
            },
            "type": item.get('type'),
            "episodes": item.get('episodes'),
            "status": item.get('status'),
            "aired": item.get('aired'),
            "score": item.get('score'),
            "scored_by": item.get('scored_by'),
            "rank": item.get('rank'),
            "popularity": item.get('popularity'),
            "members": item.get('members'),
            "favorites": item.get('favorites'),
            "source": item.get('source'),
            "season": item.get('season'),
            "year": item.get('year')
        }
        
        return self.format_item(mal_id, title, item_type, external_ids, metadata)
    
    def extract_external_ids(self, item: Dict[str, Any]) -> Dict[str, str]:
        """Extract external IDs from MAL item"""
        ids = {'mal': str(item['mal_id'])}
        
        # Check external links
        for ext in item.get('external', []):
            url = ext.get('url', '').lower()
            
            if 'anilist' in url:
                match = re.search(r'/anime/(\d+)', url)
                if match:
                    ids['anilist'] = match.group(1)
            
            elif 'anidb' in url:
                match = re.search(r'aid=(\d+)', url)
                if match:
                    ids['anidb'] = match.group(1)
        
        return ids
