"""
AniDB scraper - uses anime-lists XML as primary source
File: scrapers/anime/anidb_scraper.py
"""
import xml.etree.ElementTree as ET
from typing import Dict, List, Any
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scrapers.base_scraper import BaseScraper

class AniDBScraper(BaseScraper):
    """Scraper for AniDB data via anime-lists XML"""
    
    ANIMELISTS_URL = "https://raw.githubusercontent.com/Anime-Lists/anime-lists/refs/heads/master/anime-list-full.xml"
    
    def __init__(self):
        super().__init__("anidb", "anime")
    
    def get_rate_limit(self) -> float:
        return 1.0  # 1 second between requests
    
    def scrape(self) -> List[Dict[str, Any]]:
        """Scrape AniDB data from anime-lists XML"""
        print("Fetching anime-lists XML from GitHub...")
        
        try:
            response = self.session.get(self.ANIMELISTS_URL)
            
            if response.status_code != 200:
                raise Exception(f"Failed to fetch anime-lists: {response.status_code}")
            
            print("✓ Downloaded successfully")
            print("Parsing XML...")
            
            root = ET.fromstring(response.content)
            
            results = []
            total = len(root.findall('anime'))
            print(f"Found {total} anime entries\n")
            
            for idx, anime in enumerate(root.findall('anime'), 1):
                try:
                    anidb_id = anime.get('anidbid')
                    if not anidb_id:
                        continue
                    
                    # Extract basic info
                    name = anime.findtext('name', '')
                    
                    # Extract all IDs
                    external_ids = self.extract_external_ids(anime)
                    
                    # Build metadata
                    metadata = {
                        "name": name,
                        "tvdb_id": anime.get('tvdbid'),
                        "default_tvdb_season": anime.get('defaulttvdbseason'),
                        "tmdb_tv": anime.get('tmdbtv'),
                        "tmdb_season": anime.get('tmdbseason'),
                        "tmdb_id": anime.get('tmdbid'),
                        "imdb_id": anime.get('imdbid')
                    }
                    
                    item = self.format_item(
                        item_id=anidb_id,
                        title=name,
                        item_type="",  # Type not in anime-lists XML
                        external_ids=external_ids,
                        metadata=metadata
                    )
                    
                    results.append(item)
                    
                    if idx % 500 == 0:
                        print(f"  Processed {idx}/{total} items ({idx/total*100:.1f}%)...")
                
                except Exception as e:
                    print(f"  [WARN] Failed to process item {idx}: {e}")
                    continue
            
            print(f"\n✓ Processed all {len(results)} items")
            return results
            
        except Exception as e:
            print(f"\n[ERROR] Failed to scrape AniDB: {e}")
            raise
    
    def extract_external_ids(self, anime: ET.Element) -> Dict[str, str]:
        """Extract external IDs from anime-lists XML"""
        ids = {}
        
        # AniDB ID (self)
        if anime.get('anidbid'):
            ids['anidb'] = anime.get('anidbid')
        
        # TVDB ID
        tvdbid = anime.get('tvdbid')
        if tvdbid and tvdbid not in ['movie', 'ova', '']:
            try:
                # Validate it's a number
                int(tvdbid)
                ids['tvdb'] = tvdbid
            except (ValueError, TypeError):
                pass
        
        # TMDB - can be from tmdbtv or tmdbid
        tmdbtv = anime.get('tmdbtv')
        tmdbid = anime.get('tmdbid')
        
        if tmdbtv:
            ids['themoviedb'] = str(tmdbtv)
        elif tmdbid:
            # Handle comma-separated list - take first one
            first_id = tmdbid.split(',')[0].strip()
            if first_id and first_id.isdigit():
                ids['themoviedb'] = first_id
        
        # IMDB ID
        imdbid = anime.get('imdbid')
        if imdbid and imdbid.startswith('tt'):
            ids['imdb'] = imdbid
        
        return ids
