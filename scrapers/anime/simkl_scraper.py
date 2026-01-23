"""
SIMKL scraper using API with proper pagination via genres
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
    """Scraper for SIMKL API (requires API key)"""
    
    API_URL = "https://api.simkl.com"
    
    def __init__(self):
        super().__init__("simkl", "anime")
        # Hardcoded temp API key for testing
        self.api_key = "d7992ccbb14990741c028c9127265ebe6009dbf074c6031297717c3e588f2053"
        
        self.headers = {
            "simkl-api-key": self.api_key
        }
    
    def get_rate_limit(self) -> float:
        return 0.5
    
    def scrape(self) -> List[Dict[str, Any]]:
        """Scrape SIMKL using API endpoints with proper pagination"""
        print("Scraping SIMKL via API...")
        print("Using hardcoded API key for testing")
        print("Note: Using paginated genre endpoints for comprehensive data\n")
        
        results = []
        
        # Scrape anime and movies using paginated genre endpoints
        results.extend(self.scrape_anime_genres())
        results.extend(self.scrape_movies_genres())
        
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
    
    def scrape_anime_genres(self) -> List[Dict[str, Any]]:
        """Scrape all anime using paginated genre endpoints"""
        print("Scraping all anime via genres...")
        results = []
        
        # Comprehensive list of anime genres
        genres = [
            "action", "adventure", "comedy", "drama", "fantasy",
            "horror", "mystery", "romance", "sci-fi", "thriller",
            "slice-of-life", "supernatural", "sports", "mecha",
            "psychological", "ecchi", "harem", "josei", "kids",
            "magic", "martial-arts", "military", "music", "parody",
            "police", "school", "seinen", "shoujo", "shounen",
            "space", "super-power", "vampire", "historical",
            "dementia", "demons", "game", "samurai"
        ]
        
        total_anime = 0
        
        for genre in genres:
            page = 1
            limit = 50  # Max items per page
            genre_total = 0
            
            while True:
                try:
                    url = f"{self.API_URL}/anime/genres/{genre}"
                    params = {'page': page, 'limit': limit}
                    response = self.session.get(url, headers=self.headers, params=params)
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        # Break if no data
                        if not data or len(data) == 0:
                            break
                        
                        # Process items
                        for item in data:
                            try:
                                processed = self.process_item(item, 'anime')
                                results.append(processed)
                                genre_total += 1
                            except:
                                continue
                        
                        # Check pagination headers
                        page_count = response.headers.get('X-Pagination-Page-Count')
                        
                        # Break if we got less than limit (last page)
                        if len(data) < limit:
                            break
                        
                        # Break if we've reached max pages
                        if page_count and page >= int(page_count):
                            break
                        
                        page += 1
                        time.sleep(self.get_rate_limit())
                        
                    elif response.status_code == 404:
                        # Genre doesn't exist, skip
                        break
                    else:
                        print(f"  [WARN] Genre '{genre}' page {page}: HTTP {response.status_code}")
                        break
                        
                except Exception as e:
                    print(f"  [ERROR] Genre '{genre}' page {page}: {e}")
                    break
            
            if genre_total > 0:
                total_anime += genre_total
                print(f"  Genre '{genre}': {genre_total} items (total anime: {total_anime})")
        
        print(f"\n✓ Total anime scraped: {len(results)}")
        return results
    
    def scrape_movies_genres(self) -> List[Dict[str, Any]]:
        """Scrape all movies using paginated genre endpoints"""
        print("\nScraping all movies via genres...")
        results = []
        
        # Comprehensive list of movie genres
        genres = [
            "action", "adventure", "animation", "comedy", "crime",
            "documentary", "drama", "family", "fantasy", "history",
            "horror", "music", "mystery", "romance", "science-fiction",
            "thriller", "tv-movie", "war", "western", "biography",
            "sport", "film-noir"
        ]
        
        total_movies = 0
        
        for genre in genres:
            page = 1
            limit = 50  # Max items per page
            genre_total = 0
            
            while True:
                try:
                    url = f"{self.API_URL}/movies/genres/{genre}"
                    params = {'page': page, 'limit': limit}
                    response = self.session.get(url, headers=self.headers, params=params)
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        # Break if no data
                        if not data or len(data) == 0:
                            break
                        
                        # Process items
                        for item in data:
                            try:
                                processed = self.process_item(item, 'movie')
                                results.append(processed)
                                genre_total += 1
                            except:
                                continue
                        
                        # Check pagination headers
                        page_count = response.headers.get('X-Pagination-Page-Count')
                        
                        # Break if we got less than limit (last page)
                        if len(data) < limit:
                            break
                        
                        # Break if we've reached max pages
                        if page_count and page >= int(page_count):
                            break
                        
                        page += 1
                        time.sleep(self.get_rate_limit())
                        
                    elif response.status_code == 404:
                        # Genre doesn't exist, skip
                        break
                    else:
                        print(f"  [WARN] Genre '{genre}' page {page}: HTTP {response.status_code}")
                        break
                        
                except Exception as e:
                    print(f"  [ERROR] Genre '{genre}' page {page}: {e}")
                    break
            
            if genre_total > 0:
                total_movies += genre_total
                print(f"  Genre '{genre}': {genre_total} items (total movies: {total_movies})")
        
        print(f"\n✓ Total movies scraped: {len(results)}")
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
