"""
Kitsu scraper for manga
File: scrapers/manga/kitsu_scraper.py
"""
from typing import Dict, List, Any
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scrapers.base_scraper import BaseScraper

class KitsuMangaScraper(BaseScraper):
    """Scraper for Kitsu API (manga)"""
    
    API_URL = "https://kitsu.io/api/edge/manga"
    
    def __init__(self):
        super().__init__("kitsu", "manga")
    
    def get_rate_limit(self) -> float:
        return 0.5  # 0.5 seconds between requests
    
    def scrape(self) -> List[Dict[str, Any]]:
        """Scrape Kitsu manga data"""
        results = []
        offset = self.checkpoint.get("offset", 0)
        limit = 20
        consecutive_errors = 0
        max_consecutive_errors = 5
        
        print(f"Starting from offset {offset}...")
        
        while True:
            try:
                response = self.session.get(
                    f"{self.API_URL}?page[limit]={limit}&page[offset]={offset}",
                    headers={
                        "Accept": "application/vnd.api+json",
                        "Content-Type": "application/vnd.api+json"
                    }
                )
                
                if response.status_code != 200:
                    print(f"  [!] Error {response.status_code}. Stopping Kitsu scrape.")
                    consecutive_errors += 1
                    if consecutive_errors >= max_consecutive_errors:
                        break
                    continue
                
                consecutive_errors = 0
                data = response.json()
                items = data.get('data', [])
                
                if not items:
                    print("  No more items found")
                    break
                
                nsfw_count = sum(1 for item in items if item.get('attributes', {}).get('nsfw'))
                print(f"  Offset {offset} - {len(items)} items ({nsfw_count} NSFW)")
                
                for item in items:
                    try:
                        processed = self.process_item(item)
                        results.append(processed)
                    except Exception as e:
                        print(f"    [WARN] Failed to process item: {e}")
                
                # Save checkpoint
                self.checkpoint['offset'] = offset + limit
                self.save_checkpoint(self.checkpoint)
                
                # Check if there's a next page
                links = data.get('links', {})
                if not links.get('next'):
                    print("\n✓ Reached last page")
                    break
                
                offset += limit
                
            except Exception as e:
                print(f"  [ERROR] Offset {offset} failed: {e}")
                consecutive_errors += 1
                if consecutive_errors >= max_consecutive_errors:
                    break
        
        total_nsfw = sum(1 for item in results if item.get('metadata', {}).get('nsfw'))
        print(f"\n✓ Total items scraped: {len(results)} ({total_nsfw} NSFW)")
        
        return results
    
    def process_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Process Kitsu manga item"""
        kitsu_id = item['id']
        attrs = item.get('attributes', {})
        
        title = attrs.get('canonicalTitle', attrs.get('titles', {}).get('en', f"Unknown {kitsu_id}"))
        item_type = attrs.get('subtype', attrs.get('mangaType', ''))
        
        external_ids = self.extract_external_ids(item)
        
        metadata = {
            "titles": {
                "canonical": attrs.get('canonicalTitle'),
                "en": attrs.get('titles', {}).get('en'),
                "en_jp": attrs.get('titles', {}).get('en_jp'),
                "ja_jp": attrs.get('titles', {}).get('ja_jp')
            },
            "subtype": attrs.get('subtype'),
            "status": attrs.get('status'),
            "chapter_count": attrs.get('chapterCount'),
            "volume_count": attrs.get('volumeCount'),
            "started_at": attrs.get('startDate'),
            "ended_at": attrs.get('endDate'),
            "average_rating": attrs.get('averageRating'),
            "user_count": attrs.get('userCount'),
            "favorites_count": attrs.get('favoritesCount'),
            "popularity_rank": attrs.get('popularityRank'),
            "rating_rank": attrs.get('ratingRank'),
            "age_rating": attrs.get('ageRating'),
            "age_rating_guide": attrs.get('ageRatingGuide'),
            "serialization": attrs.get('serialization'),
            "nsfw": attrs.get('nsfw', False)
        }
        
        return self.format_item(kitsu_id, title, item_type, external_ids, metadata)
    
    def extract_external_ids(self, item: Dict[str, Any]) -> Dict[str, str]:
        """Extract external IDs from Kitsu manga item"""
        ids = {'kitsu': str(item['id'])}
        
        # Kitsu doesn't provide external IDs directly
        # These would need to be fetched from mappings
        
        return ids
