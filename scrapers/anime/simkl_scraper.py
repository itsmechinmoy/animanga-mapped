"""
SIMKL scraper for anime (requires API key)
File: scrapers/anime/simkl_scraper.py
"""
from typing import Dict, List, Any
import sys
from pathlib import Path
import os
import time

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scrapers.base_scraper import BaseScraper

class SIMKLAnimeScraper(BaseScraper):
    """Scraper for SIMKL API (anime + movies)"""
    
    API_URL = "https://api.simkl.com"
    
    def __init__(self):
        super().__init__("simkl", "anime")
        self.api_key = os.getenv("SIMKL_CLIENT_ID")
        
        if not self.api_key:
            print("[WARN] SIMKL_CLIENT_ID environment variable not set")
            print("[WARN] SIMKL scraping will be limited")
        
        self.headers = {
            "simkl-api-key": self.api_key if self.api_key else ""
        }
    
    def get_rate_limit(self) -> float:
        return 0.5  # 0.5 seconds between requests
    
    def scrape(self) -> List[Dict[str, Any]]:
        """
        Scrape SIMKL anime data
        SIMKL doesn't have a direct 'list all' endpoint
        We'll use multiple approaches:
        1. Search by year/season
        2. Get trending/popular lists
        3. Use genre-based queries
        """
        results = []
        
        if not self.api_key:
            print("[!] Cannot scrape SIMKL without API key")
            print("[!] Set SIMKL_CLIENT_ID environment variable")
            return results
        
        print("Note: SIMKL scraping uses multiple discovery methods")
        print("This will take longer than other services\n")
        
        # Method 1: Get by year (2000-2026)
        results.extend(self.scrape_by_years())
        
        # Method 2: Get popular/trending
        results.extend(self.scrape_popular())
        
        # Deduplicate by SIMKL ID
        seen_ids = set()
        unique_results = []
        for item in results:
            simkl_id = item.get('id')
            if simkl_id and simkl_id not in seen_ids:
                seen_ids.add(simkl_id)
                unique_results.append(item)
        
        print(f"\n✓ Total unique items found: {len(unique_results)}")
        return unique_results
    
    def scrape_by_years(self) -> List[Dict[str, Any]]:
        """Scrape anime by year"""
        print("Scraping by year (2000-2026)...")
        results = []
        
        start_year = self.checkpoint.get("last_year", 2000)
        
        for year in range(start_year, 2027):
            try:
                print(f"  Year {year}...")
                
                # Anime
                anime_url = f"{self.API_URL}/search/anime?year={year}"
                response = self.session.get(anime_url, headers=self.headers)
                
                if response.status_code == 200:
                    data = response.json()
                    for item in data:
                        try:
                            processed = self.process_item(item, 'anime')
                            results.append(processed)
                        except Exception as e:
                            continue
                
                # Movies
                movie_url = f"{self.API_URL}/search/movie?year={year}"
                response = self.session.get(movie_url, headers=self.headers)
                
                if response.status_code == 200:
                    data = response.json()
                    for item in data:
                        try:
                            processed = self.process_item(item, 'movie')
                            results.append(processed)
                        except Exception as e:
                            continue
                
                # Save checkpoint
                self.checkpoint['last_year'] = year
                self.save_checkpoint(self.checkpoint)
                
                time.sleep(1)  # Extra delay between years
                
            except Exception as e:
                print(f"    [WARN] Year {year} failed: {e}")
                continue
        
        print(f"  Found {len(results)} items by year")
        return results
    
    def scrape_popular(self) -> List[Dict[str, Any]]:
        """Scrape popular/trending anime"""
        print("\nScraping popular/trending...")
        results = []
        
        endpoints = [
            "/anime/trending",
            "/anime/popular",
            "/movies/trending",
            "/movies/popular"
        ]
        
        for endpoint in endpoints:
            try:
                url = f"{self.API_URL}{endpoint}"
                response = self.session.get(url, headers=self.headers)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    for item in data:
                        try:
                            media_type = 'movie' if 'movies' in endpoint else 'anime'
                            processed = self.process_item(item, media_type)
                            results.append(processed)
                        except Exception as e:
                            continue
                
                print(f"  {endpoint}: {len(data)} items")
                
            except Exception as e:
                print(f"  [WARN] {endpoint} failed: {e}")
                continue
        
        print(f"  Found {len(results)} popular items")
        return results
    
    def process_item(self, item: Dict[str, Any], media_type: str) -> Dict[str, Any]:
        """Process a SIMKL item"""
        # Get IDs
        ids = item.get('ids', {})
        simkl_id = ids.get('simkl') or ids.get('simkl_id')
        
        if not simkl_id:
            raise ValueError("No SIMKL ID found")
        
        # Get title
        title = item.get('title', f"Unknown {simkl_id}")
        
        # Get type
        item_type = item.get('type', media_type.upper())
        
        # Extract external IDs
        external_ids = self.extract_external_ids(item)
        
        # Build metadata
        metadata = {
            "title": title,
            "year": item.get('year'),
            "type": item.get('type'),
            "status": item.get('status'),
            "total_episodes": item.get('total_episodes'),
            "anime_type": item.get('anime_type'),
            "genres": item.get('genres', []),
            "ratings": item.get('ratings'),
            "rank": item.get('rank'),
            "en_title": item.get('en_title'),
            "poster": item.get('poster')
        }
        
        return self.format_item(simkl_id, title, item_type, external_ids, metadata)
    
    def extract_external_ids(self, item: Dict[str, Any]) -> Dict[str, str]:
        """Extract external IDs from SIMKL item"""
        ids = item.get('ids', {})
        
        external_ids = {
            'simkl': str(ids.get('simkl') or ids.get('simkl_id', ''))
        }
        
        # MAL ID
        if ids.get('mal'):
            external_ids['mal'] = str(ids['mal'])
        
        # AniList ID
        if ids.get('anilist'):
            external_ids['anilist'] = str(ids['anilist'])
        
        # AniDB ID
        if ids.get('anidb'):
            external_ids['anidb'] = str(ids['anidb'])
        
        # TMDB ID
        if ids.get('tmdb'):
            external_ids['themoviedb'] = str(ids['tmdb'])
        
        # IMDB ID
        if ids.get('imdb'):
            external_ids['imdb'] = ids['imdb']
        
        # TVDB ID
        if ids.get('tvdb') or ids.get('slug'):
            # SIMKL uses slug for TVDB, not ID
            if ids.get('tvdb'):
                external_ids['tvdb'] = str(ids['tvdb'])
        
        return external_ids
