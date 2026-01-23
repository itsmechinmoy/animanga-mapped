"""
SIMKL scraper using API with proper pagination
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
        self.api_key = "3f0e5e44090724e73112649ebae18791e8e1ce7ed541ccc3896b9d236560ef02"
        
        self.headers = {
            "simkl-api-key": self.api_key
        }
    
    def get_rate_limit(self) -> float:
        return 0.5
    
    def scrape(self) -> List[Dict[str, Any]]:
        """Scrape SIMKL using API endpoints with proper pagination"""
        if not self.api_key:
            print("[!] Cannot scrape SIMKL without API key")
            return []
        
        print("Scraping SIMKL via API...")
        print("Note: Using paginated endpoints for comprehensive data\n")
        
        results = []
        
        # Scrape anime and movies using paginated endpoints
        results.extend(self.scrape_anime_all())
        results.extend(self.scrape_movies_all())
        
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
    
    def scrape_anime_all(self) -> List[Dict[str, Any]]:
        """Scrape all anime using paginated /anime/all endpoint"""
        print("Scraping all anime...")
        results = []
        page = 1
        limit = 50  # Max per page
        
        while True:
            try:
                url = f"{self.API_URL}/anime/all"
                params = {
                    'page': page,
                    'limit': limit
                }
                
                response = self.session.get(url, headers=self.headers, params=params)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Check if we got any data
                    if not data or len(data) == 0:
                        print(f"  Reached end at page {page}")
                        break
                    
                    # Process items
                    for item in data:
                        try:
                            processed = self.process_item(item, 'anime')
                            results.append(processed)
                        except Exception as e:
                            continue
                    
                    print(f"  Page {page}: {len(data)} items (total: {len(results)})")
                    
                    # Check pagination headers
                    page_count = response.headers.get('X-Pagination-Page-Count')
                    if page_count and page >= int(page_count):
                        print(f"  Completed all {page_count} pages")
                        break
                    
                    # If we got less than limit, we're done
                    if len(data) < limit:
                        print(f"  Last page reached (received {len(data)} < {limit})")
                        break
                    
                    page += 1
                    time.sleep(self.get_rate_limit())
                    
                elif response.status_code == 404:
                    print(f"  Endpoint not available, trying alternative method")
                    return self.scrape_anime_genres()
                else:
                    print(f"  Error {response.status_code} on page {page}")
                    break
                    
            except Exception as e:
                print(f"  [ERROR] Page {page} failed: {e}")
                break
        
        return results
    
    def scrape_movies_all(self) -> List[Dict[str, Any]]:
        """Scrape all movies using paginated /movies/all endpoint"""
        print("\nScraping all movies...")
        results = []
        page = 1
        limit = 50  # Max per page
        
        while True:
            try:
                url = f"{self.API_URL}/movies/all"
                params = {
                    'page': page,
                    'limit': limit
                }
                
                response = self.session.get(url, headers=self.headers, params=params)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Check if we got any data
                    if not data or len(data) == 0:
                        print(f"  Reached end at page {page}")
                        break
                    
                    # Process items
                    for item in data:
                        try:
                            processed = self.process_item(item, 'movie')
                            results.append(processed)
                        except Exception as e:
                            continue
                    
                    print(f"  Page {page}: {len(data)} items (total: {len(results)})")
                    
                    # Check pagination headers
                    page_count = response.headers.get('X-Pagination-Page-Count')
                    if page_count and page >= int(page_count):
                        print(f"  Completed all {page_count} pages")
                        break
                    
                    # If we got less than limit, we're done
                    if len(data) < limit:
                        print(f"  Last page reached (received {len(data)} < {limit})")
                        break
                    
                    page += 1
                    time.sleep(self.get_rate_limit())
                    
                elif response.status_code == 404:
                    print(f"  Endpoint not available, trying alternative method")
                    return self.scrape_movies_genres()
                else:
                    print(f"  Error {response.status_code} on page {page}")
                    break
                    
            except Exception as e:
                print(f"  [ERROR] Page {page} failed: {e}")
                break
        
        return results
    
    def scrape_anime_genres(self) -> List[Dict[str, Any]]:
        """Fallback: Scrape anime by genre with pagination"""
        print("\nScraping anime by genres (fallback method)...")
        results = []
        
        genres = [
            "action", "adventure", "comedy", "drama", "fantasy",
            "horror", "mystery", "romance", "sci-fi", "thriller",
            "slice-of-life", "supernatural", "sports", "mecha",
            "psychological", "ecchi", "harem", "josei", "kids",
            "magic", "martial-arts", "military", "music", "parody",
            "police", "school", "seinen", "shoujo", "shounen",
            "space", "super-power", "vampire", "historical"
        ]
        
        for genre in genres:
            page = 1
            limit = 50
            genre_total = 0
            
            while True:
                try:
                    url = f"{self.API_URL}/anime/genres/{genre}"
                    params = {'page': page, 'limit': limit}
                    response = self.session.get(url, headers=self.headers, params=params)
                    
                    if response.status_code == 200:
                        data = response.json()
                        if not data or len(data) == 0:
                            break
                        
                        for item in data:
                            try:
                                processed = self.process_item(item, 'anime')
                                results.append(processed)
                                genre_total += 1
                            except:
                                continue
                        
                        if len(data) < limit:
                            break
                        
                        page += 1
                        time.sleep(self.get_rate_limit())
                    else:
                        break
                        
                except Exception:
                    break
            
            if genre_total > 0:
                print(f"  Genre '{genre}': {genre_total} items")
        
        return results
    
    def scrape_movies_genres(self) -> List[Dict[str, Any]]:
        """Fallback: Scrape movies by genre with pagination"""
        print("\nScraping movies by genres (fallback method)...")
        results = []
        
        genres = [
            "action", "adventure", "animation", "comedy", "crime",
            "documentary", "drama", "family", "fantasy", "history",
            "horror", "music", "mystery", "romance", "science-fiction",
            "thriller", "tv-movie", "war", "western"
        ]
        
        for genre in genres:
            page = 1
            limit = 50
            genre_total = 0
            
            while True:
                try:
                    url = f"{self.API_URL}/movies/genres/{genre}"
                    params = {'page': page, 'limit': limit}
                    response = self.session.get(url, headers=self.headers, params=params)
                    
                    if response.status_code == 200:
                        data = response.json()
                        if not data or len(data) == 0:
                            break
                        
                        for item in data:
                            try:
                                processed = self.process_item(item, 'movie')
                                results.append(processed)
                                genre_total += 1
                            except:
                                continue
                        
                        if len(data) < limit:
                            break
                        
                        page += 1
                        time.sleep(self.get_rate_limit())
                    else:
                        break
                        
                except Exception:
                    break
            
            if genre_total > 0:
                print(f"  Genre '{genre}': {genre_total} items")
        
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
