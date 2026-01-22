"""
SIMKL scraper using API only (web scraping gets blocked)
File: scrapers/anime/simkl_scraper.py
"""
from typing import Dict, List, Any
import sys
from pathlib import Path
import os

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
            "simkl-api-key": self.api_key if self.api_key else ""
        }
    
    def get_rate_limit(self) -> float:
        return 0.5
    
    def scrape(self) -> List[Dict[str, Any]]:
        """Scrape SIMKL using API endpoints"""
        if not self.api_key:
            print("[!] Cannot scrape SIMKL without API key")
            return []
        
        print("Scraping SIMKL via API...")
        print("Note: Limited by available public endpoints\n")
        
        results = []
        
        # Available SIMKL API endpoints
        results.extend(self.scrape_lists())
        results.extend(self.scrape_genres())
        
        # Deduplicate
        seen_ids = set()
        unique_results = []
        for item in results:
            simkl_id = item.get('id')
            if simkl_id and simkl_id not in seen_ids:
                seen_ids.add(simkl_id)
                unique_results.append(item)
        
        print(f"\n✓ Total unique items: {len(unique_results)}")
        return unique_results
    
    def scrape_lists(self) -> List[Dict[str, Any]]:
        """Scrape from trending/popular lists"""
        print("Scraping lists...")
        results = []
        
        endpoints = [
            ("/anime/trending", "anime"),
            ("/anime/popular", "anime"),
            ("/movies/trending", "movie"),
        ]
        
        for endpoint, media_type in endpoints:
            try:
                url = f"{self.API_URL}{endpoint}"
                response = self.session.get(url, headers=self.headers)
                
                if response.status_code == 200:
                    data = response.json()
                    for item in data:
                        try:
                            processed = self.process_item(item, media_type)
                            results.append(processed)
                        except:
                            continue
                    print(f"  {endpoint}: {len(data)} items")
                elif response.status_code == 404:
                    print(f"  {endpoint}: Not available")
                
            except Exception as e:
                print(f"  [WARN] {endpoint} failed: {e}")
        
        return results
    
    def scrape_genres(self) -> List[Dict[str, Any]]:
        """Scrape by genre"""
        print("\nScraping genres...")
        results = []
        
        genres = [
            "action", "adventure", "comedy", "drama", "fantasy",
            "horror", "mystery", "romance", "sci-fi", "thriller",
            "slice-of-life", "supernatural", "sports", "mecha"
        ]
        
        for genre in genres:
            try:
                url = f"{self.API_URL}/anime/genres/{genre}"
                response = self.session.get(url, headers=self.headers)
                
                if response.status_code == 200:
                    data = response.json()
                    count = 0
                    for item in data[:100]:  # Limit per genre
                        try:
                            processed = self.process_item(item, 'anime')
                            results.append(processed)
                            count += 1
                        except:
                            continue
                    print(f"  Genre '{genre}': {count} items")
                
            except Exception as e:
                continue
        
        return results
    
    def process_item(self, item: Dict[str, Any], media_type: str) -> Dict[str, Any]:
        """Process SIMKL item"""
        ids = item.get('ids', {})
        simkl_id = ids.get('simkl') or ids.get('simkl_id')
        
        if not simkl_id:
            raise ValueError("No SIMKL ID")
        
        title = item.get('title', f"Unknown {simkl_id}")
        item_type = item.get('type', media_type.upper())
        
        external_ids = self.extract_external_ids(item)
        
        metadata = {
            "title": title,
            "year": item.get('year'),
            "type": item.get('type'),
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
