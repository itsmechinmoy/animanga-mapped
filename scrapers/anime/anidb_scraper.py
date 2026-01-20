"""
AniDB scraper - uses anime-lists XML as primary source
"""
import xml.etree.ElementTree as ET
from typing import Dict, List, Any
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
        print("Fetching anime-lists XML...")
        
        response = self.session.get(self.ANIMELISTS_URL)
        
        if response.status_code != 200:
            raise Exception(f"Failed to fetch anime-lists: {response.status_code}")
        
        print("Parsing XML...")
        root = ET.fromstring(response.content)
        
        results = []
        total = len(root.findall('anime'))
        
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
                
                if idx % 100 == 0:
                    print(f"  Processed {idx}/{total} items...")
            
            except Exception as e:
                print(f"  [WARN] Failed to process item: {e}")
                continue
        
        return results
    
    def extract_external_ids(self, anime: ET.Element) -> Dict[str, str]:
        """Extract external IDs from anime-lists XML"""
        ids = {}
        
        # AniDB ID (self)
        if anime.get('anidbid'):
            ids['anidb'] = anime.get('anidbid')
        
        # TVDB ID
        tvdbid = anime.get('tvdbid')
        if tvdbid and tvdbid not in ['movie', 'ova']:
            ids['tvdb'] = tvdbid
        
        # TMDB - can be from tmdbtv or tmdbid
        tmdbtv = anime.get('tmdbtv')
        tmdbid = anime.get('tmdbid')
        if tmdbtv:
            ids['themoviedb'] = tmdbtv
        elif tmdbid:
            # Handle comma-separated list - take first one
            ids['themoviedb'] = tmdbid.split(',')[0]
        
        # IMDB ID
        if anime.get('imdbid'):
            ids['imdb'] = anime.get('imdbid')
        
        return ids
