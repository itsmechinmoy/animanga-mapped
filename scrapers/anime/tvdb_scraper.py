"""
TVDB (The TV Database) scraper
File: scrapers/anime/tvdb_scraper.py
"""
from typing import Dict, List, Any
import sys
from pathlib import Path
import os

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scrapers.base_scraper import BaseScraper

class TVDBScraper(BaseScraper):
    """Scraper for TVDB API v4 (requires API key)"""
    
    API_URL = "https://api4.thetvdb.com/v4"
    
    def __init__(self):
        super().__init__("tvdb", "anime")
        self.api_key = os.getenv("TVDB_API_KEY")
        self.token = None
        
        if not self.api_key:
            print("[WARN] TVDB_API_KEY environment variable not set")
            print("[WARN] TVDB scraping will not work")
    
    def get_rate_limit(self) -> float:
        return 1.0  # 1 second between requests
    
    def authenticate(self) -> bool:
        """Authenticate with TVDB API"""
        if not self.api_key:
            return False
        
        try:
            response = self.session.post(
                f"{self.API_URL}/login",
                json={"apikey": self.api_key}
            )
            
            if response.status_code == 200:
                data = response.json()
                self.token = data.get('data', {}).get('token')
                
                # Update session headers
                self.session.session.headers.update({
                    'Authorization': f'Bearer {self.token}'
                })
                
                return True
        except Exception as e:
            print(f"[!] Authentication failed: {e}")
        
        return False
    
    def scrape(self) -> List[Dict[str, Any]]:
        """Scrape TVDB anime data"""
        if not self.api_key:
            print("[!] Cannot scrape TVDB without API key")
            print("[!] Set TVDB_API_KEY environment variable")
            return []
        
        if not self.authenticate():
            print("[!] Failed to authenticate with TVDB")
            return []
        
        print("Scraping TVDB anime...")
        print("Note: Filtering by Japanese language\n")
        
        results = []
        page = self.checkpoint.get("page", 0)
        
        while True:
            try:
                # Search for anime (Japanese series)
                url = f"{self.API_URL}/series"
                params = {
                    'page': page,
                    'lang': 'jpn'  # Japanese
                }
                
                response = self.session.get(url, params=params)
                
                if response.status_code != 200:
                    print(f"  [!] HTTP {response.status_code}")
                    break
                
                data = response.json()
                items = data.get('data', [])
                
                if not items:
                    print("  No more items found")
                    break
                
                print(f"  Page {page} - {len(items)} items")
                
                for item in items:
                    try:
                        processed = self.process_item(item)
                        if processed:
                            results.append(processed)
                    except Exception as e:
                        continue
                
                # Save checkpoint
                self.checkpoint['page'] = page + 1
                self.save_checkpoint(self.checkpoint)
                
                # Check pagination
                links = data.get('links', {})
                if not links.get('next'):
                    print("\n  Reached last page")
                    break
                
                page += 1
                
            except Exception as e:
                print(f"  [ERROR] Page {page} failed: {e}")
                break
        
        print(f"\n✓ Processed {len(results)} items")
        return results
    
    def process_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Process TVDB item"""
        tvdb_id = item.get('id')
        if not tvdb_id:
            return None
        
        title = item.get('name', f"Unknown {tvdb_id}")
        item_type = "TV"  # TVDB is primarily TV series
        
        # Get external IDs
        external_ids = self.extract_external_ids(item)
        external_ids['tvdb'] = str(tvdb_id)
        
        # Metadata
        metadata = {
            "name": item.get('name'),
            "slug": item.get('slug'),
            "overview": item.get('overview'),
            "first_aired": item.get('firstAired'),
            "status": item.get('status'),
            "original_language": item.get('originalLanguage'),
            "year": item.get('year')
        }
        
        return self.format_item(tvdb_id, title, item_type, external_ids, metadata)
    
    def extract_external_ids(self, item: Dict[str, Any]) -> Dict[str, str]:
        """Extract external IDs from TVDB item"""
        ids = {}
        
        # TVDB includes remote IDs
        remote_ids = item.get('remoteIds', [])
        for remote in remote_ids:
            source = remote.get('sourceName', '').lower()
            remote_id = remote.get('id')
            
            if not remote_id:
                continue
            
            if 'imdb' in source:
                ids['imdb'] = remote_id
            elif 'tmdb' in source or 'themoviedb' in source:
                ids['themoviedb'] = str(remote_id)
            elif 'anidb' in source:
                ids['anidb'] = str(remote_id)
        
        return ids
