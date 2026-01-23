"""
Kitsu scraper for manga
File: scrapers/manga/kitsu_scraper.py
"""
from typing import Dict, List, Any
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scrapers.base_scraper import BaseScraper

class KitsuMangaScraper(BaseScraper):
    """Scraper for Kitsu API (manga)"""
    
    API_URL = "https://kitsu.io/api/edge/manga"
    AUTH_URL = "https://kitsu.io/api/oauth/token"
    
    def __init__(self):
        # Initialize auth token as None before parent init
        self.auth_header = {}
        super().__init__("kitsu", "manga")
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate with Kitsu to access NSFW content"""
        email = os.getenv("KITSU_EMAIL")
        password = os.getenv("KITSU_PASSWORD")

        if not email or not password:
            print("  [WARN] KITSU_EMAIL or KITSU_PASSWORD not found. NSFW content will be hidden.")
            return

        try:
            print("  Authenticating with Kitsu...")
            response = self.session.post(
                self.AUTH_URL,
                json={
                    "grant_type": "password",
                    "username": email,
                    "password": password
                },
                headers={"Content-Type": "application/json"}
            )

            if response.status_code == 200:
                token = response.json().get("access_token")
                self.auth_header = {"Authorization": f"Bearer {token}"}
                print("  ✓ Authentication successful (NSFW content enabled)")
            else:
                print(f"  [!] Authentication failed (Status: {response.status_code}). Continuing as guest.")
        except Exception as e:
            print(f"  [!] Authentication error: {e}")
    
    def get_rate_limit(self) -> float:
        return 0.5
    
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
                headers = {
                    "Accept": "application/vnd.api+json",
                    "Content-Type": "application/vnd.api+json"
                }
                headers.update(self.auth_header)

                # Added &include=mappings to fetch external IDs
                response = self.session.get(
                    f"{self.API_URL}?page[limit]={limit}&page[offset]={offset}&include=mappings",
                    headers=headers
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
                
                # Create mappings lookup from 'included' section
                included = data.get('included', [])
                mapping_lookup = {
                    item['id']: item['attributes']
                    for item in included
                    if item.get('type') == 'mappings'
                }
                
                if not items:
                    print("  No more items found")
                    break
                
                print(f"  Offset {offset} - {len(items)} items")
                
                for item in items:
                    try:
                        processed = self.process_item(item, mapping_lookup)
                        results.append(processed)
                    except Exception as e:
                        print(f"    [WARN] Failed to process item: {e}")
                
                self.checkpoint['offset'] = offset + limit
                self.save_checkpoint(self.checkpoint)
                
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
        
        return results
    
    def process_item(self, item: Dict[str, Any], mapping_lookup: Dict[str, Any] = None) -> Dict[str, Any]:
        """Process Kitsu manga item"""
        kitsu_id = item['id']
        attrs = item.get('attributes', {})
        
        title = attrs.get('canonicalTitle', attrs.get('titles', {}).get('en', f"Unknown {kitsu_id}"))
        item_type = attrs.get('subtype', attrs.get('mangaType', ''))
        
        # Pass lookup to extract_external_ids
        external_ids = self.extract_external_ids(item, mapping_lookup)
        
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
            "serialization": attrs.get('serialization')
        }
        
        return self.format_item(kitsu_id, title, item_type, external_ids, metadata)
    
    def extract_external_ids(self, item: Dict[str, Any], mapping_lookup: Dict[str, Any] = None) -> Dict[str, str]:
        """Extract external IDs from Kitsu manga item"""
        ids = {'kitsu': str(item['id'])}
        
        if not mapping_lookup:
            return ids
            
        # Get mapping relationships
        mappings_rel = item.get('relationships', {}).get('mappings', {}).get('data', [])
        
        for mapping_ref in mappings_rel:
            m_id = mapping_ref.get('id')
            if m_id and m_id in mapping_lookup:
                mapping_data = mapping_lookup[m_id]
                site = mapping_data.get('externalSite')
                ext_id = mapping_data.get('externalId')
                
                if not site or not ext_id:
                    continue
                    
                # Normalize site names to standard keys
                # Kitsu returns 'myanimelist/manga', 'anilist', 'mangaupdates', etc.
                if 'myanimelist' in site:
                    ids['mal'] = str(ext_id)
                elif 'anilist' in site:
                    ids['anilist'] = str(ext_id)
        
        return ids
