"""
SIMKL scraper using anime-offline-database
Gets 14,253+ SIMKL entries with full cross-references
File: scrapers/anime/simkl_scraper.py
"""
from typing import Dict, List, Any
import sys
from pathlib import Path
import json
import re

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scrapers.base_scraper import BaseScraper

class SIMKLAnimeScraper(BaseScraper):
    """Scraper for SIMKL using anime-offline-database"""
    
    # Use the minified version for faster download
    DATABASE_URL = "https://github.com/manami-project/anime-offline-database/releases/latest/download/anime-offline-database-minified.json"
    
    def __init__(self):
        super().__init__("simkl", "anime")
    
    def get_rate_limit(self) -> float:
        return 1.0
    
    def scrape(self) -> List[Dict[str, Any]]:
        """Scrape SIMKL data from anime-offline-database"""
        print("="*70)
        print("SIMKL SCRAPER - Using anime-offline-database")
        print("="*70)
        print("Fetching anime-offline-database from GitHub releases...")
        print("This may take a moment (downloading ~40,000 entries)...\n")
        
        try:
            response = self.session.get(self.DATABASE_URL)
            
            if response.status_code != 200:
                raise Exception(f"Failed to fetch database: {response.status_code}")
            
            print("✓ Downloaded successfully")
            print("Parsing JSON...")
            
            database = response.json()
            all_anime = database.get('data', [])
            
            print(f"✓ Loaded {len(all_anime)} total anime entries")
            print(f"Database last updated: {database.get('lastUpdate', 'unknown')}\n")
            
            results = []
            simkl_count = 0
            
            print("Extracting SIMKL entries...")
            
            for idx, anime in enumerate(all_anime, 1):
                try:
                    # Find SIMKL URL in sources
                    simkl_url = self.find_simkl_source(anime.get('sources', []))
                    
                    if not simkl_url:
                        continue
                    
                    # Extract SIMKL ID from URL
                    simkl_id = self.extract_simkl_id(simkl_url)
                    if not simkl_id:
                        continue
                    
                    simkl_count += 1
                    
                    # Extract all external IDs
                    external_ids = self.extract_external_ids(anime.get('sources', []))
                    external_ids['simkl'] = simkl_id
                    
                    # Build metadata
                    metadata = {
                        "title": anime.get('title'),
                        "type": anime.get('type'),
                        "episodes": anime.get('episodes'),
                        "status": anime.get('status'),
                        "synonyms": anime.get('synonyms', []),
                        "picture": anime.get('picture'),
                        "thumbnail": anime.get('thumbnail'),
                        "year": anime.get('animeSeason', {}).get('year'),
                        "season": anime.get('animeSeason', {}).get('season'),
                        "studios": anime.get('studios', []),
                        "producers": anime.get('producers', []),
                        "tags": anime.get('tags', []),
                        "score": anime.get('score'),
                        "duration": anime.get('duration'),
                    }
                    
                    item = self.format_item(
                        item_id=simkl_id,
                        title=anime.get('title', f'Unknown {simkl_id}'),
                        item_type=anime.get('type', 'UNKNOWN'),
                        external_ids=external_ids,
                        metadata=metadata
                    )
                    
                    results.append(item)
                    
                    if simkl_count % 500 == 0:
                        print(f"  Found {simkl_count} SIMKL entries so far...")
                
                except Exception as e:
                    continue
            
            print(f"\n{'='*70}")
            print(f"✓ Total SIMKL entries extracted: {len(results)}")
            print(f"✓ Coverage: {simkl_count}/{len(all_anime)} entries have SIMKL IDs")
            print("="*70)
            
            return results
            
        except Exception as e:
            print(f"\n[ERROR] Failed to scrape: {e}")
            raise
    
    def find_simkl_source(self, sources: List[str]) -> str:
        """Find SIMKL URL in sources list"""
        for source in sources:
            if 'simkl.com' in source:
                return source
        return ""
    
    def extract_simkl_id(self, url: str) -> str:
        """Extract SIMKL ID from URL"""
        # URL format: https://simkl.com/anime/40190
        match = re.search(r'simkl\.com/(?:anime|tv|movies?)/(\d+)', url)
        if match:
            return match.group(1)
        return ""
    
    def extract_external_ids(self, sources: List[str]) -> Dict[str, str]:
        """Extract all external IDs from sources"""
        ids = {}
        
        for source in sources:
            # MyAnimeList
            if 'myanimelist.net' in source:
                match = re.search(r'myanimelist\.net/anime/(\d+)', source)
                if match:
                    ids['mal'] = match.group(1)
            
            # AniList
            elif 'anilist.co' in source:
                match = re.search(r'anilist\.co/anime/(\d+)', source)
                if match:
                    ids['anilist'] = match.group(1)
            
            # AniDB
            elif 'anidb.net' in source:
                match = re.search(r'anidb\.net/anime/(\d+)', source)
                if match:
                    ids['anidb'] = match.group(1)
            
            # Kitsu
            elif 'kitsu.app' in source or 'kitsu.io' in source:
                match = re.search(r'kitsu\.(?:app|io)/anime/(\d+)', source)
                if match:
                    ids['kitsu'] = match.group(1)
            
            # TVDB (from animecountdown which uses TVDB IDs)
            elif 'animecountdown.com' in source:
                match = re.search(r'animecountdown\.com/(\d+)', source)
                if match:
                    ids['tvdb'] = match.group(1)
            
            # LiveChart
            elif 'livechart.me' in source:
                match = re.search(r'livechart\.me/anime/(\d+)', source)
                if match:
                    ids['livechart'] = match.group(1)
            
            # Anime-Planet
            elif 'anime-planet.com' in source:
                match = re.search(r'anime-planet\.com/anime/([\w-]+)', source)
                if match:
                    ids['animeplanet'] = match.group(1)
            
            # AniSearch
            elif 'anisearch.com' in source:
                match = re.search(r'anisearch\.com/anime/(\d+)', source)
                if match:
                    ids['anisearch'] = match.group(1)
            
            # Anime News Network
            elif 'animenewsnetwork.com' in source:
                match = re.search(r'id=(\d+)', source)
                if match:
                    ids['ann'] = match.group(1)
        
        return ids
