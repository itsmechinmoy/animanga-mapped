"""
SIMKL scraper using API only (Optimized with Key Rotation & Smart Pagination)
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
    
    GENRES = [
        "action", "adventure", "animation", "comedy", "crime", "documentary", 
        "drama", "family", "fantasy", "history", "horror", "music", "mystery", 
        "romance", "science-fiction", "thriller", "war", "western", "anime"
    ]

    def __init__(self):
        super().__init__("simkl", "anime")
        
        # KEY ROTATION SYSTEM
        # We load the Env Var, plus the backup key you provided
        env_key = os.getenv("SIMKL_CLIENT_ID")
        self.api_keys = []
        
        if env_key:
            self.api_keys.append(env_key)
        
        # Add the 'scrape 2' key as backup
        backup_key = "3f0e5e44090724e73112649ebae18791e8e1ce7ed541ccc3896b9d236560ef02"
        if backup_key not in self.api_keys:
            self.api_keys.append(backup_key)
            
        self.current_key_index = 0
        self.seen_ids = set()
        self.stop_scraping = False
    
    def get_current_headers(self):
        if not self.api_keys:
            return {}
        return {
            "simkl-api-key": self.api_keys[self.current_key_index],
            "Content-Type": "application/json"
        }
    
    def rotate_key(self):
        """Switches to the next API key if available"""
        if self.current_key_index + 1 < len(self.api_keys):
            self.current_key_index += 1
            print(f"  [♻️] 412 Limit Hit. Rotating to API Key #{self.current_key_index + 1}...")
            return True
        else:
            print(f"  [⛔] All API keys exhausted (412). Stopping script.")
            self.stop_scraping = True
            return False

    def get_rate_limit(self) -> float:
        return 1.2
    
    def scrape(self) -> List[Dict[str, Any]]:
        if not self.api_keys:
            print("[!] No SIMKL_CLIENT_ID found.")
            return []
        
        print(f"Scraping SIMKL via API (Keys available: {len(self.api_keys)})...")
        results = []
        
        # 1. Scrape Anime (Use Efficient Mode: Try 'All' first, split only if needed)
        if not self.stop_scraping:
            print("\n--- Scraping Anime Catalog ---")
            results.extend(self.scrape_catalog("anime", efficient_mode=True))

        # 2. Scrape Movies (Movies are huge, efficient mode might fail often, but worth trying)
        if not self.stop_scraping:
            print("\n--- Scraping Movies Catalog ---")
            results.extend(self.scrape_catalog("movies", efficient_mode=True))
        
        print(f"\n✓ Total unique items scraped: {len(results)}")
        return results

    def scrape_catalog(self, media_type: str, efficient_mode: bool = False) -> List[Dict[str, Any]]:
        results = []
        current_year = datetime.datetime.now().year + 1
        start_year = 1980
        
        base_endpoint = f"/anime/genres" if media_type == "anime" else f"/movies/genres"

        for year in range(current_year, start_year - 1, -1):
            if self.stop_scraping: break
            
            print(f"\n>>> Processing {media_type.capitalize()} Year: {year}")
            
            # --- STRATEGY 1: Efficient Mode (Grab everything for the year) ---
            if efficient_mode:
                # Returns True if fully scraped, False if we hit a limit/too many items
                success = self.scrape_genre_endpoint(base_endpoint, "all", year, media_type, results, check_limit=True)
                
                if success:
                    # If successful, we don't need to loop genres. We got it all.
                    continue
                elif self.stop_scraping:
                    break
                else:
                    print(f"  [!] 'All' contained too many items (>1000). Splitting by Genre...")

            # --- STRATEGY 2: Fallback (Split by Genre) ---
            for genre in self.GENRES:
                if self.stop_scraping: break
                self.scrape_genre_endpoint(base_endpoint, genre, year, media_type, results, check_limit=False)
            
        return results

    def scrape_genre_endpoint(self, base_endpoint, genre, year, media_type, results_list, check_limit=False) -> bool:
        """
        Scrapes a specific endpoint. 
        If check_limit=True, it aborts if it detects page > 20 (Simkl Limit), returning False.
        """
        page = 1
        items_found = 0
        
        while True:
            if self.stop_scraping: break

            try:
                url = f"{self.API_URL}{base_endpoint}/{genre}"
                params = {
                    "release": year, # The critical fix: 'release' not 'year'
                    "page": page,
                    "limit": 50,
                    "sort": "rank"
                }
                
                # Use current key headers
                response = self.session.get(url, headers=self.get_current_headers(), params=params)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if not data:
                        break # End of pages
                    
                    # Safety: Check if API ignored the 'release' filter
                    if data[0].get('year') and abs(data[0]['year'] - year) > 2:
                         # API returned 1990 items for 2024 request. Filter broken.
                        return False

                    for item in data:
                        try:
                            s_id = item.get('ids', {}).get('simkl')
                            if s_id and s_id not in self.seen_ids:
                                processed = self.process_item(item, media_type)
                                results_list.append(processed)
                                self.seen_ids.add(s_id)
                                items_found += 1
                        except:
                            continue
                    
                    # Pagination Logic
                    if len(data) < 50:
                        break # Last page reached naturally
                    
                    # LIMIT CHECK: Simkl generally 412s if page > 20 (1000 items)
                    # If we are in "Efficient Mode" (genre='all') and hit Page 19,
                    # we should stop and tell the main loop to use Genres instead.
                    if check_limit and page >= 18:
                        return False 
                        
                    page += 1
                    time.sleep(self.get_rate_limit())
                    
                elif response.status_code == 404:
                    return True # Genre empty, technically success
                
                elif response.status_code == 412:
                    # If we hit 412, try rotating keys
                    if self.rotate_key():
                        # Retry the exact same request with new key
                        continue 
                    else:
                        return False

                elif response.status_code == 429:
                    print(f"  [!] 429 Too Many Requests. Sleeping 10s...")
                    time.sleep(10)
                    continue 
                else:
                    print(f"  [!] Error {response.status_code} on {url}")
                    return False
                    
            except Exception as e:
                print(f"  [!] Request failed: {e}")
                return False
        
        if items_found > 0:
            print(f"  {genre}: {items_found} items")
        return True

    def process_item(self, item: Dict[str, Any], media_type: str) -> Dict[str, Any]:
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
        ids = item.get('ids', {})
        external_ids = {'simkl': str(ids.get('simkl') or ids.get('simkl_id', ''))}
        
        if ids.get('mal'): external_ids['mal'] = str(ids['mal'])
        if ids.get('anilist'): external_ids['anilist'] = str(ids['anilist'])
        if ids.get('anidb'): external_ids['anidb'] = str(ids['anidb'])
        if ids.get('tmdb'): external_ids['themoviedb'] = str(ids['tmdb'])
        if ids.get('imdb'): external_ids['imdb'] = ids['imdb']
        if ids.get('tvdb'): external_ids['tvdb'] = str(ids['tvdb'])
        
        return external_ids
