"""
SIMKL scraper using API only (web scraping gets blocked)
File: scrapers/anime/simkl_scraper.py
"""
from typing import Dict, List, Any
import sys
from pathlib import Path
import os
import time
import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scrapers.base_scraper import BaseScraper

class SIMKLAnimeScraper(BaseScraper):
    """Scraper for SIMKL API (requires API key)"""
    
    API_URL = "https://api.simkl.com"
    
    def __init__(self):
        super().__init__("simkl", "anime")
        self.api_key = os.getenv("SIMKL_CLIENT_ID")
        
        if not self.api_key:
            print("[WARN] SIMKL_CLIENT_ID environment variable not set")
        
        self.headers = {
            "simkl-api-key": self.api_key if self.api_key else "",
            "Content-Type": "application/json"
        }
        self.stop_scraping = False
    
    def get_rate_limit(self) -> float:
        return 1.5  # Increased delay to avoid 429/412 errors
    
    def scrape(self) -> List[Dict[str, Any]]:
        """Scrape SIMKL using API endpoints"""
        if not self.api_key:
            print("[!] Cannot scrape SIMKL without API key")
            return []
        
        print("Scraping SIMKL via API...")
        results = []
        
        # 1. Scrape Anime Catalog
        if not self.stop_scraping:
            print("\n--- Scraping Anime Catalog ---")
            results.extend(self.scrape_catalog("anime"))

        # 2. Scrape Movies Catalog
        if not self.stop_scraping:
            print("\n--- Scraping Movies Catalog ---")
            results.extend(self.scrape_catalog("movies"))
        
        # Deduplicate
        seen_ids = set()
        unique_results = []
        for item in results:
            s_id = item.get('id') or item.get('simkl_id') 
            if s_id and s_id not in seen_ids:
                seen_ids.add(s_id)
                unique_results.append(item)
        
        print(f"\n✓ Total unique items: {len(unique_results)}")
        return unique_results

    def scrape_catalog(self, media_type: str) -> List[Dict[str, Any]]:
        """
        Iterate through years using the 'release' parameter.
        """
        results = []
        current_year = datetime.datetime.now().year + 1
        start_year = 1990 
        
        # Docs: "Genres API duplicates the urls of the Genres on the website"
        endpoint = f"/anime/genres/all" if media_type == "anime" else f"/movies/genres/all"

        for year in range(current_year, start_year - 1, -1):
            if self.stop_scraping:
                break
                
            page = 1
            year_count = 0
            
            print(f"Processing {media_type.capitalize()} Year: {year}...")
            
            while True:
                if self.stop_scraping:
                    break

                try:
                    url = f"{self.API_URL}{endpoint}"
                    
                    # CRITICAL FIX: Use 'release' instead of 'year'
                    params = {
                        "release": year,  
                        "page": page,
                        "limit": 50, 
                        "sort": "rank" 
                    }
                    
                    response = self.session.get(url, headers=self.headers, params=params)
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        if not data:
                            break 
                        
                        # SAFETY CHECK: Verify the API is actually filtering
                        # If we are on page 1 and the first item's year is wildly different, 
                        # the filter is failing. Abort to save quota.
                        if page == 1 and data:
                            first_item_year = data[0].get('year')
                            if first_item_year and abs(first_item_year - year) > 1:
                                print(f"  [!] API IGNORING FILTER: Requested {year}, got {first_item_year}. Aborting year.")
                                break

                        for item in data:
                            try:
                                processed = self.process_item(item, media_type)
                                results.append(processed)
                                year_count += 1
                            except Exception:
                                continue
                        
                        # Pagination Check
                        if len(data) < 50:
                            break
                            
                        page += 1
                        time.sleep(self.get_rate_limit())
                        
                    elif response.status_code == 412:
                        print(f"  [!!!] CRITICAL: Rate limit/Quota exceeded (412). Stopping script.")
                        self.stop_scraping = True
                        break
                    elif response.status_code == 429:
                        print(f"  [!] Rate limit hit on page {page}. Sleeping 10s...")
                        time.sleep(10)
                        continue 
                    else:
                        print(f"  [!] Error {response.status_code} on {url}")
                        break
                        
                except Exception as e:
                    print(f"  [!] Request failed: {e}")
                    break
            
            print(f"  Finished {year}: found {year_count} items")
            
        return results

    def process_item(self, item: Dict[str, Any], media_type: str) -> Dict[str, Any]:
        """Process SIMKL item"""
        ids = item.get('ids', {})
        simkl_id = ids.get('simkl') or ids.get('simkl_id')
        
        if not simkl_id:
            raise ValueError("No SIMKL ID")
        
        title = item.get('title', f"Unknown {simkl_id}")
        item_type = item.get('anime_type') or item.get('type') or media_type
        
        external_ids = self.extract_external_ids(item)
        
        metadata = {
            "title": title,
            "year": item.get('year'),
            "type": item_type,
            "status": item.get('status'),
            "total_episodes": item.get('total_episodes'),
            "genres": item.get('genres', []),
            "ratings": item.get('ratings'),
        }
        
        return self.format_item(simkl_id, title, item_type, external_ids, metadata)
    
    def extract_external_ids(self, item: Dict[str, Any]) -> Dict[str, str]:
        """Extract external IDs"""
        ids = item.get('ids', {})
        external_ids = {'simkl': str(ids.get('simkl') or ids.get('simkl_id', ''))}
        
        # Map common IDs
        if ids.get('mal'): external_ids['mal'] = str(ids['mal'])
        if ids.get('anilist'): external_ids['anilist'] = str(ids['anilist'])
        if ids.get('anidb'): external_ids['anidb'] = str(ids['anidb'])
        if ids.get('tmdb'): external_ids['themoviedb'] = str(ids['tmdb'])
        if ids.get('imdb'): external_ids['imdb'] = ids['imdb']
        if ids.get('tvdb'): external_ids['tvdb'] = str(ids['tvdb'])
        
        return external_ids
