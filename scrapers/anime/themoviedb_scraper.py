"""
TMDB (The Movie Database) scraper for anime
File: scrapers/anime/themoviedb_scraper.py
"""
from typing import Dict, List, Any
import sys
from pathlib import Path
import os
import re

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scrapers.base_scraper import BaseScraper

class TMDBAnimeScraper(BaseScraper):
    """Scraper for TMDB API (requires API key)"""
    
    API_URL = "https://api.themoviedb.org/3"
    
    def __init__(self):
        super().__init__("themoviedb", "anime")
        self.api_key = os.getenv("TMDB_API_KEY")
        
        if not self.api_key:
            print("[WARN] TMDB_API_KEY environment variable not set")
            print("[WARN] TMDB scraping will not work")
    
    def get_rate_limit(self) -> float:
        return 0.25  # 4 requests per second allowed
    
    def scrape(self) -> List[Dict[str, Any]]:
        """Scrape TMDB anime data"""
        if not self.api_key:
            print("[!] Cannot scrape TMDB without API key")
            print("[!] Set TMDB_API_KEY environment variable")
            return []
        
        print("Scraping TMDB anime...")
        results = []
        
        # TMDB doesn't have an "anime" category directly
        # We need to search for anime using keywords and genres
        
        # Approach 1: Search with "anime" keyword
        results.extend(self.search_by_keyword("anime"))
        
        # Approach 2: Discover with animation genre (ID: 16) and Japanese language
        results.extend(self.discover_anime())
        
        # Deduplicate
        seen_ids = set()
        unique_results = []
        for item in results:
            tmdb_id = item.get('id')
            if tmdb_id and tmdb_id not in seen_ids:
                seen_ids.add(tmdb_id)
                unique_results.append(item)
        
        print(f"\n✓ Total unique items: {len(unique_results)}")
        return unique_results
    
    def search_by_keyword(self, keyword: str) -> List[Dict[str, Any]]:
        """Search TMDB by keyword"""
        print(f"\nSearching by keyword: '{keyword}'...")
        results = []
        
        page = self.checkpoint.get("search_page", 1)
        max_pages = 100  # Limit search
        
        while page <= max_pages:
            try:
                url = f"{self.API_URL}/search/tv"
                params = {
                    'api_key': self.api_key,
                    'query': keyword,
                    'page': page,
                    'language': 'en-US'
                }
                
                response = self.session.get(url, params=params)
                
                if response.status_code != 200:
                    break
                
                data = response.json()
                items = data.get('results', [])
                
                if not items:
                    break
                
                print(f"  Page {page}/{data.get('total_pages', '?')} - {len(items)} items")
                
                for item in items:
                    try:
                        processed = self.process_item(item, 'tv')
                        results.append(processed)
                    except Exception as e:
                        continue
                
                if page >= data.get('total_pages', 0):
                    break
                
                page += 1
                self.checkpoint['search_page'] = page
                self.save_checkpoint(self.checkpoint)
                
            except Exception as e:
                print(f"    [ERROR] Page {page} failed: {e}")
                break
        
        return results
    
    def discover_anime(self) -> List[Dict[str, Any]]:
        """Discover anime using TMDB discover endpoint"""
        print("\nDiscovering anime (Animation + Japanese)...")
        results = []
        
        page = self.checkpoint.get("discover_page", 1)
        max_pages = 500
        
        while page <= max_pages:
            try:
                url = f"{self.API_URL}/discover/tv"
                params = {
                    'api_key': self.api_key,
                    'with_genres': 16,  # Animation
                    'with_original_language': 'ja',  # Japanese
                    'page': page,
                    'sort_by': 'popularity.desc'
                }
                
                response = self.session.get(url, params=params)
                
                if response.status_code != 200:
                    break
                
                data = response.json()
                items = data.get('results', [])
                
                if not items:
                    break
                
                print(f"  Page {page}/{data.get('total_pages', '?')} - {len(items)} items")
                
                for item in items:
                    try:
                        processed = self.process_item(item, 'tv')
                        results.append(processed)
                    except Exception as e:
                        continue
                
                if page >= data.get('total_pages', 0):
                    break
                
                page += 1
                self.checkpoint['discover_page'] = page
                self.save_checkpoint(self.checkpoint)
                
            except Exception as e:
                print(f"    [ERROR] Page {page} failed: {e}")
                break
        
        return results
    
    def process_item(self, item: Dict[str, Any], media_type: str) -> Dict[str, Any]:
        """Process TMDB item"""
        tmdb_id = item['id']
        title = item.get('name') or item.get('title', f"Unknown {tmdb_id}")
        item_type = media_type.upper()
        
        # Get external IDs
        external_ids = self.get_external_ids(tmdb_id, media_type)
        external_ids['themoviedb'] = str(tmdb_id)
        
        # Metadata
        metadata = {
            "name": item.get('name'),
            "original_name": item.get('original_name'),
            "overview": item.get('overview'),
            "first_air_date": item.get('first_air_date'),
            "popularity": item.get('popularity'),
            "vote_average": item.get('vote_average'),
            "vote_count": item.get('vote_count'),
            "origin_country": item.get('origin_country', []),
            "original_language": item.get('original_language')
        }
        
        return self.format_item(tmdb_id, title, item_type, external_ids, metadata)
    
    def get_external_ids(self, tmdb_id: int, media_type: str) -> Dict[str, str]:
        """Get external IDs for a TMDB item"""
        ids = {}
        
        try:
            url = f"{self.API_URL}/{media_type}/{tmdb_id}/external_ids"
            params = {'api_key': self.api_key}
            
            response = self.session.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('imdb_id'):
                    ids['imdb'] = data['imdb_id']
                
                if data.get('tvdb_id'):
                    ids['tvdb'] = str(data['tvdb_id'])
        
        except Exception as e:
            pass
        
        return ids
    
    def extract_external_ids(self, item: Dict[str, Any]) -> Dict[str, str]:
        """Extract external IDs"""
        # Done in process_item
        return {}
