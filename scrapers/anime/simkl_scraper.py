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
    
    def get_rate_limit(self) -> float:
        return 0.8  # Slight increase to be safe with pagination loops
    
    def scrape(self) -> List[Dict[str, Any]]:
        """Scrape SIMKL using API endpoints"""
        if not self.api_key:
            print("[!] Cannot scrape SIMKL without API key")
            return []
        
        print("Scraping SIMKL via API...")
        results = []
        
        # 1. Scrape Anime Catalog
        print("\n--- Scraping Anime Catalog ---")
        results.extend(self.scrape_catalog("anime"))

        # 2. Scrape Movies Catalog
        print("\n--- Scraping Movies Catalog ---")
        results.extend(self.scrape_catalog("movies"))
        
        # Deduplicate
        seen_ids = set()
        unique_results = []
        for item in results:
            # Create a unique key based on SIMKL ID and Type
            simkl_id = item.get('simkl_id') # format_item puts id in top level or mapped_id
            # If format_item structure varies, check where ID is stored. 
            # BaseScraper usually expects mapped data. 
            # Let's rely on the ID present in the mapped dictionary.
            
            # Extract ID from the formatted item to ensure uniqueness
            # The format_item method typically returns dict with 'id', 'title' etc.
            # We need to check how your base scraper expects it, but usually:
            s_id = item.get('id') or item.get('simkl_id') 

            if s_id and s_id not in seen_ids:
                seen_ids.add(s_id)
                unique_results.append(item)
        
        print(f"\n✓ Total unique items: {len(unique_results)}")
        return unique_results

    def scrape_catalog(self, media_type: str) -> List[Dict[str, Any]]:
        """
        Iterate through years and pages to get comprehensive coverage.
        Using /genres/all endpoint which mimics the 'All' filter on the website.
        """
        results = []
        current_year = datetime.datetime.now().year + 2
        start_year = 1990 # Adjust as needed. Pre-1990 anime exists but is less dense.
        
        # Define the endpoint based on media type
        # Docs: "Genres API duplicates the urls of the Genres on the website"
        # Website: https://simkl.com/anime/all/ -> API: /anime/genres/all
        endpoint = f"/anime/genres/all" if media_type == "anime" else f"/movies/genres/all"

        # Iterate by year to avoid deep pagination limits
        for year in range(current_year, start_year - 1, -1):
            page = 1
            year_count = 0
            
            print(f"Processing {media_type.capitalize()} Year: {year}...")
            
            while True:
                try:
                    url = f"{self.API_URL}{endpoint}"
                    params = {
                        "year": year,
                        "page": page,
                        "limit": 50, # Max limit per docs usually 50
                        # "sort": "rank" # Optional: sort by rank/popularity
                    }
                    
                    response = self.session.get(url, headers=self.headers, params=params)
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        if not data:
                            break # No more pages for this year
                            
                        # Process items
                        for item in data:
                            try:
                                # For movies endpoint, type might be 'movie'
                                # For anime endpoint, type might be 'tv', 'ova', etc.
                                processed = self.process_item(item, media_type)
                                results.append(processed)
                                year_count += 1
                            except Exception as e:
                                # print(f"Error processing item: {e}")
                                continue
                        
                        # Pagination Check
                        # If we received fewer items than limit, we are on the last page
                        if len(data) < 50:
                            break
                            
                        page += 1
                        time.sleep(self.get_rate_limit()) # Respect rate limit
                        
                    elif response.status_code == 429:
                        print(f"  [!] Rate limit hit on page {page}. Sleeping 5s...")
                        time.sleep(5)
                        continue # Retry same page
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
        
        # Determine strict type
        # For anime endpoint, simkl distinguishes 'tv', 'movie', 'ova' in 'anime_type' usually
        # But 'type' field in response usually holds 'anime', 'movie', 'show'
        # We want to preserve the specific anime type if available (ova, ona, etc)
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
        
        if ids.get('mal'):
            external_ids['mal'] = str(ids['mal'])
        if ids.get('anilist'):
            external_ids['anilist'] = str(ids['anilist'])
        if ids.get('anidb'):
            external_ids['anidb'] = str(ids['anidb'])
        if ids.get('tmdb'):
            external_ids['themoviedb'] = str(ids['tmdb'])
        if ids.get('imdb'):
            external_ids['imdb'] = ids['imdb']
        if ids.get('tvdb'):
            external_ids['tvdb'] = str(ids['tvdb'])
        
        return external_ids
