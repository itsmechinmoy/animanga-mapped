"""
MyAnimeList manga scraper using Jikan API v4
File: scrapers/manga/myanimelist_scraper.py
"""
from typing import Dict, List, Any
import sys
from pathlib import Path
import time

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scrapers.base_scraper import BaseScraper

class MyAnimeListMangaScraper(BaseScraper):
    """Scraper for MyAnimeList manga via Jikan API"""
    
    API_URL = "https://api.jikan.moe/v4/manga"
    
    def __init__(self):
        super().__init__("myanimelist", "manga")
    
    def get_rate_limit(self) -> float:
        return 1.0  # Jikan has strict rate limits
    
    def scrape(self) -> List[Dict[str, Any]]:
        """Scrape MAL manga data via Jikan"""
        results = []
        page = self.checkpoint.get("page", 1)
        consecutive_errors = 0
        max_consecutive_errors = 5
        
        print(f"Starting from page {page}...")
        print("Note: Jikan API has strict rate limits. This may take a while.\n")
        
        while True:
            try:
                response = self.session.get(
                    f"{self.API_URL}?page={page}&limit=25"
                )
                
                if response.status_code == 429:
                    print("  [!] Rate limited. Waiting 60 seconds...")
                    time.sleep(60)
                    continue
                
                if response.status_code != 200:
                    print(f"  [!] HTTP {response.status_code}. Waiting 10 seconds...")
                    time.sleep(10)
                    consecutive_errors += 1
                    if consecutive_errors >= max_consecutive_errors:
                        print(f"  [!] Too many consecutive errors. Stopping.")
                        break
                    continue
                
                consecutive_errors = 0
                data = response.json()
                
                if 'data' not in data or not data['data']:
                    print("  No more items found")
                    break
                
                items = data['data']
                pagination = data.get('pagination', {})
                
                current = pagination.get('current_page', page)
                last = pagination.get('last_visible_page', '?')
                print(f"  Page {current}/{last} - {len(items)} items")
                
                for item in items:
                    try:
                        processed = self.process_item(item)
                        results.append(processed)
                    except Exception as e:
                        print(f"    [WARN] Failed to process item: {e}")
                
                # Save checkpoint
                self.checkpoint['page'] = page + 1
                self.save_checkpoint(self.checkpoint)
                
                if not pagination.get('has_next_page'):
                    print("\n✓ Reached last page")
                    break
                
                page += 1
                
            except Exception as e:
                print(f"  [ERROR] Page {page} failed: {e}")
                consecutive_errors += 1
                if consecutive_errors >= max_consecutive_errors:
                    break
                time.sleep(10)
        
        return results
    
    def process_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single MAL manga item"""
        mal_id = item['mal_id']
        title = item.get('title', item.get('title_english', f"Unknown {mal_id}"))
        item_type = item.get('type', '')
        
        external_ids = self.extract_external_ids(item)
        
        metadata = {
            "titles": {
                "default": item.get('title'),
                "english": item.get('title_english'),
                "japanese": item.get('title_japanese'),
                "synonyms": item.get('title_synonyms', [])
            },
            "type": item.get('type'),
            "chapters": item.get('chapters'),
            "volumes": item.get('volumes'),
            "status": item.get('status'),
            "publishing": item.get('publishing'),
            "published": item.get('published'),
            "score": item.get('score'),
            "scored_by": item.get('scored_by'),
            "rank": item.get('rank'),
            "popularity": item.get('popularity'),
            "members": item.get('members'),
            "favorites": item.get('favorites'),
            "authors": item.get('authors', []),
            "serializations": item.get('serializations', []),
            "genres": item.get('genres', []),
            "themes": item.get('themes', []),
            "demographics": item.get('demographics', [])
        }
        
        return self.format_item(mal_id, title, item_type, external_ids, metadata)
    
    def extract_external_ids(self, item: Dict[str, Any]) -> Dict[str, str]:
        """Extract external IDs from MAL manga item"""
        ids = {'mal': str(item['mal_id'])}
        
        # Check external links if available
        for ext in item.get('external', []):
            url = ext.get('url', '').lower()
            
            if not url:
                continue
            
            try:
                import re
                
                if 'anilist' in url:
                    match = re.search(r'/manga/(\d+)', url)
                    if match:
                        ids['anilist'] = match.group(1)
                
                elif 'kitsu' in url:
                    match = re.search(r'/manga/(\d+)', url)
                    if match:
                        ids['kitsu'] = match.group(1)
            except:
                pass
        
        return ids
