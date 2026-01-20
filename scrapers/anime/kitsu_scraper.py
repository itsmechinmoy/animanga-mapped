"""
Kitsu scraper for anime
"""
from typing import Dict, List, Any
from scrapers.base_scraper import BaseScraper

class KitsuScraper(BaseScraper):
    """Scraper for Kitsu API"""
    
    API_URL = "https://kitsu.io/api/edge/anime"
    
    def __init__(self):
        super().__init__("kitsu", "anime")
    
    def get_rate_limit(self) -> float:
        return 0.5
    
    def scrape(self) -> List[Dict[str, Any]]:
        """Scrape Kitsu data"""
        results = []
        offset = self.checkpoint.get("offset", 0)
        limit = 20
        
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
                    print(f"  Error {response.status_code}. Stopping.")
                    break
                
                data = response.json()
                items = data.get('data', [])
                
                if not items:
                    break
                
                print(f"  Offset {offset} - {len(items)} items")
                
                for item in items:
                    processed = self.process_item(item)
                    results.append(processed)
                
                # Save checkpoint
                self.checkpoint['offset'] = offset + limit
                self.save_checkpoint(self.checkpoint)
                
                offset += limit
                
            except Exception as e:
                print(f"  [ERROR] Offset {offset} failed: {e}")
                break
        
        return results
    
    def process_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Process Kitsu item"""
        kitsu_id = item['id']
        attrs = item.get('attributes', {})
        
        title = attrs.get('canonicalTitle', '')
        item_type = attrs.get('subtype', '')
        
        external_ids = {'kitsu': kitsu_id}
        
        metadata = {
            "titles": {
                "canonical": attrs.get('canonicalTitle'),
                "english": attrs.get('titles', {}).get('en'),
                "japanese": attrs.get('titles', {}).get('ja_jp')
            },
            "subtype": attrs.get('subtype'),
            "status": attrs.get('status'),
            "episode_count": attrs.get('episodeCount'),
            "started_at": attrs.get('startDate'),
            "ended_at": attrs.get('endDate'),
            "rating": attrs.get('averageRating'),
            "user_count": attrs.get('userCount'),
            "favorites_count": attrs.get('favoritesCount'),
            "popularity_rank": attrs.get('popularityRank'),
            "rating_rank": attrs.get('ratingRank')
        }
        
        return self.format_item(kitsu_id, title, item_type, external_ids, metadata)
    
    def extract_external_ids(self, item: Dict[str, Any]) -> Dict[str, str]:
        """Kitsu doesn't provide external IDs directly"""
        return {}
