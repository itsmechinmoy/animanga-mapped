"""
AniList scraper for manga
File: scrapers/manga/anilist_scraper.py
"""
from typing import Dict, List, Any
import sys
from pathlib import Path
import re
import time

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scrapers.base_scraper import BaseScraper

class AniListMangaScraper(BaseScraper):
    """Scraper for AniList API (manga)"""
    
    API_URL = "https://graphql.anilist.co"
    
    QUERY = """
    query ($page: Int) {
      Page(page: $page, perPage: 50) {
        pageInfo { hasNextPage currentPage lastPage }
        media(type: MANGA, sort: ID) {
          id idMal format status chapters volumes
          title { romaji english native }
          startDate { year month day }
          endDate { year month day }
          source countryOfOrigin
          externalLinks { url site }
        }
      }
    }
    """
    
    def __init__(self):
        super().__init__("anilist", "manga")
    
    def get_rate_limit(self) -> float:
        return 1.0  # 1 second between requests
    
    def scrape(self) -> List[Dict[str, Any]]:
        """Scrape AniList manga data"""
        results = []
        page = self.checkpoint.get("page", 1)
        
        print(f"Starting from page {page}...")
        
        while True:
            try:
                response = self.session.post(
                    self.API_URL,
                    json={
                        'query': self.QUERY,
                        'variables': {'page': page}
                    },
                    headers={'Content-Type': 'application/json', 'Accept': 'application/json'}
                )
                
                data = response.json()
                
                if 'errors' in data:
                    print(f"  [ERROR] GraphQL errors: {data['errors']}")
                    if any('rate limit' in str(err).lower() for err in data['errors']):
                        print("  Rate limited. Waiting 60s...")
                        time.sleep(60)
                        continue
                    break
                
                page_data = data.get('data', {}).get('Page', {})
                media_list = page_data.get('media', [])
                page_info = page_data.get('pageInfo', {})
                
                if not media_list:
                    print("  No more items found")
                    break
                
                current = page_info.get('currentPage', page)
                last = page_info.get('lastPage', '?')
                print(f"  Page {current}/{last} - {len(media_list)} items")
                
                for media in media_list:
                    try:
                        item = self.process_media(media)
                        results.append(item)
                    except Exception as e:
                        print(f"    [WARN] Failed to process media {media.get('id')}: {e}")
                
                # Save checkpoint
                self.checkpoint['page'] = page + 1
                self.save_checkpoint(self.checkpoint)
                
                if not page_info.get('hasNextPage'):
                    print("\n✓ Reached last page")
                    break
                
                page += 1
                
            except Exception as e:
                print(f"  [ERROR] Page {page} failed: {e}")
                self.checkpoint['page'] = page
                self.save_checkpoint(self.checkpoint)
                break
        
        return results
    
    def process_media(self, media: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single media item"""
        anilist_id = media['id']
        
        title_data = media.get('title', {})
        title = (title_data.get('romaji') or 
                title_data.get('english') or 
                title_data.get('native') or 
                f"Unknown {anilist_id}")
        
        item_type = media.get('format', '')
        
        external_ids = self.extract_external_ids(media)
        
        metadata = {
            "titles": title_data,
            "format": media.get('format'),
            "status": media.get('status'),
            "chapters": media.get('chapters'),
            "volumes": media.get('volumes'),
            "start_date": media.get('startDate'),
            "end_date": media.get('endDate'),
            "source": media.get('source'),
            "country": media.get('countryOfOrigin')
        }
        
        return self.format_item(
            item_id=anilist_id,
            title=title,
            item_type=item_type,
            external_ids=external_ids,
            metadata=metadata
        )
    
    def extract_external_ids(self, media: Dict[str, Any]) -> Dict[str, str]:
        """Extract external IDs from AniList media"""
        ids = {
            'anilist': str(media['id'])
        }
        
        # MAL ID
        if media.get('idMal'):
            ids['mal'] = str(media['idMal'])
        
        # Parse external links
        for link in media.get('externalLinks', []):
            site = link.get('site', '').lower()
            url = link.get('url', '')
            
            if not url:
                continue
            
            try:
                if 'kitsu' in site:
                    match = re.search(r'/manga/(\d+)', url) or re.search(r'/manga/([^/?]+)', url)
                    if match:
                        ids['kitsu'] = match.group(1)
                
                elif 'anime-planet' in site or 'animeplanet' in site:
                    match = re.search(r'/manga/([^/?]+)', url)
                    if match:
                        ids['animeplanet'] = match.group(1)
                
            except Exception:
                continue
        
        return ids
