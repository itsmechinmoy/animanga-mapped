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
    
    # Standard Simkl Genres
    GENRES = [
        "action", "adventure", "animation", "comedy", "crime", "documentary", 
        "drama", "family", "fantasy", "history", "horror", "music", "mystery", 
        "romance", "science-fiction", "thriller", "war", "western", "anime"
    ]

    def __init__(self):
        super().__init__("simkl", "anime")
        self.api_key = os.getenv("SIMKL_CLIENT_ID")
        self.seen_ids = set() # Global deduplication
        
        if not self.api_key:
            print("[WARN] SIMKL_CLIENT_ID environment variable not set")
        
        self.headers = {
            "simkl-api-key": self.api_key if self.api_key else "",
            "Content-Type": "application/json"
        }
        self.stop_scraping = False
    
    def get_rate_limit(self) -> float:
        return 1.2 
    
    def scrape(self) -> List[Dict[str, Any]]:
        """Scrape SIMKL using API endpoints"""
        if not self.api_key:
            print("[!] Cannot scrape SIMKL without API key")
            return []
        
        print("Scraping SIMKL via API...")
        results = []
        
        # 1. Scrape Anime (Usually smaller, can arguably do just by year, but safety first)
        if not self.stop_scraping:
            print("\n--- Scraping Anime Catalog ---")
            results.extend(self.scrape_catalog("anime"))

        # 2. Scrape Movies (Huge, definitely needs Genre + Year splitting)
        if not self.stop_scraping:
            print("\n--- Scraping Movies Catalog ---")
            results.extend(self.scrape_catalog("movies"))
        
        print(f"\n✓ Total unique items scraped: {len(results)}")
        return results

    def scrape_catalog(self, media_type: str) -> List[Dict[str, Any]]:
        """
        Iterate through Years AND Genres to keep pagination shallow.
        """
        results = []
        current_year = datetime.datetime.now().year + 1
        start_year = 1980 # Adjust based on how deep you want to go
        
        # For anime, we can iterate just by year usually, but 'genres/all' failed you before.
        # We will iterate genres for both to be safe.
        base_endpoint = f"/anime/genres" if media_type == "anime" else f"/movies/genres"

        for year in range(current_year, start_year - 1, -1):
            if self.stop_scraping: break
            
            print(f"\n>>> Processing {media_type.capitalize()} Year: {year}")
            
            # Loop genres within the year to keep list size < 2000 (Simkl pagination limit)
            for genre in self.GENRES:
                if self.stop_scraping: break
                
                # Check if genre exists for this media type (simple heuristic or try/catch)
                page = 1
                items_found_in_genre = 0
                
                while True:
                    if self.stop_scraping: break

                    try:
                        # Construct URL: /anime/genres/{slug}
                        url = f"{self.API_URL}{base_endpoint}/{genre}"
                        
                        params = {
                            "release": year,    # The critical fix: 'release' not 'year'
                            "page": page,
                            "limit": 50,
                            "sort": "rank"      # Ensure popular items come first
                        }
                        
                        response = self.session.get(url, headers=self.headers, params=params)
                        
                        if response.status_code == 200:
                            data = response.json()
                            
                            # SAFETY CHECK: If empty or API ignored filter
                            if not data:
                                break
                                
                            # Double check the API isn't ignoring 'release' param
                            # If we asked for 2024 and got 1990, the filter failed.
                            first_item_year = data[0].get('year')
                            if first_item_year and abs(first_item_year - year) > 2:
                                # Allow slight deviation for release dates vs production year
                                print(f"  [!] API ignored filter (Asked {year}, got {first_item_year}). Skipping...")
                                break

                            for item in data:
                                try:
                                    s_id = item.get('ids', {}).get('simkl')
                                    if s_id and s_id not in self.seen_ids:
                                        processed = self.process_item(item, media_type)
                                        results.append(processed)
                                        self.seen_ids.add(s_id)
                                        items_found_in_genre += 1
                                except Exception:
                                    continue
                            
                            # Pagination Check
                            if len(data) < 50:
                                break
                            
                            # Safety limit: Simkl rarely allows > 20 pages (1000 items) per filter
                            if page > 30: 
                                break
                                
                            page += 1
                            time.sleep(self.get_rate_limit())
                            
                        elif response.status_code == 404:
                            # Genre might not exist for this media type
                            break
                        elif response.status_code == 412:
                            print(f"  [!] Rate/Pagination limit hit (412). Skipping rest of {genre}...")
                            break 
                        elif response.status_code == 429:
                            print(f"  [!] 429 Too Many Requests. Sleeping 10s...")
                            time.sleep(10)
                            continue 
                        else:
                            print(f"  [!] Error {response.status_code} on {url}")
                            break
                            
                    except Exception as e:
                        print(f"  [!] Request failed: {e}")
                        break
                
                if items_found_in_genre > 0:
                    print(f"  {genre}: {items_found_in_genre} new items")
            
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
        
        if ids.get('mal'): external_ids['mal'] = str(ids['mal'])
        if ids.get('anilist'): external_ids['anilist'] = str(ids['anilist'])
        if ids.get('anidb'): external_ids['anidb'] = str(ids['anidb'])
        if ids.get('tmdb'): external_ids['themoviedb'] = str(ids['tmdb'])
        if ids.get('imdb'): external_ids['imdb'] = ids['imdb']
        if ids.get('tvdb'): external_ids['tvdb'] = str(ids['tvdb'])
        
        return external_ids
