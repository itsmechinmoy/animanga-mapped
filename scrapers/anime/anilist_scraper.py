"""
AniList scraper for anime
File: scrapers/anime/anilist_scraper.py
"""
from typing import Dict, List, Any
import sys
from pathlib import Path
import re
import time

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scrapers.base_scraper import BaseScraper

class AniListAnimeScraper(BaseScraper):
    """Scraper for AniList API (anime)"""
    
    API_URL = "https://graphql.anilist.co"
    
    QUERY = """
    query ($page: Int) {
      Page(page: $page, perPage: 50) {
        pageInfo { hasNextPage currentPage lastPage }
        media(type: ANIME, sort: ID) {
          id idMal format status episodes
          title { romaji english native }
          startDate { year month day }
          endDate { year month day }
          season seasonYear
          source countryOfOrigin
          externalLinks { url site }
        }
      }
    }
    """
    
    def __init__(self):
        super().__init__("anilist", "anime")
    
    def get_rate_limit(self) -> float:
        return 1.0  # 1 second between requests
    
    def scrape(self) -> List[Dict[str, Any]]:
        """Scrape AniList anime data"""
        results = []
        page = self.checkpoint.get("page", 1)
        
        print(f"Starting from page {page}...")
        
        while True:
            try:
                response = self.session.post(
                    self.API_URL,
                    json={
                        'query': self.QUERY,
                        'variables': {'page': page}
                    },
                    headers={'Content-Type': 'application/json', 'Accept': 'application/json'}
                )
                
                data = response.json()
                
                if 'errors' in data:
                    print(f"  [ERROR] GraphQL errors: {data['errors']}")
                    # Check if it's a rate limit error
                    if any('rate limit' in str(err).lower() for err in data['errors']):
                        print("  Rate limited. Waiting 60s...")
                        time.sleep(60)
                        continue
                    break
                
                page_data = data.get('data', {}).get('Page', {})
                media_list = page_data.get('media', [])
                page_info = page_data.get('pageInfo', {})
                
                if not media_list:
                    print("  No more items found")
                    break
                
                current = page_info.get('currentPage', page)
                last = page_info.get('lastPage', '?')
                print(f"  Page {current}/{last} - {len(media_list)} items")
                
                for media in media_list:
                    try:
                        item = self.process_media(media)
                        results.append(item)
                    except Exception as e:
                        print(f"    [WARN] Failed to process media {media.get('id')}: {e}")
                
                # Save checkpoint after each page
                self.checkpoint['page'] = page + 1
                self.save_checkpoint(self.checkpoint)
                
                if not page_info.get('hasNextPage'):
                    print("\n✓ Reached last page")
                    break
                
                page += 1
                
            except Exception as e:
                print(f"  [ERROR] Page {page} failed: {e}")
                # Save what we have so far
                self.checkpoint['page'] = page
                self.save_checkpoint(self.checkpoint)
                break
        
        return results
    
    def process_media(self, media: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single media item"""
        anilist_id = media['id']
        
        # Get best available title
        title_data = media.get('title', {})
        title = (title_data.get('romaji') or 
                title_data.get('english') or 
                title_data.get('native') or 
                f"Unknown {anilist_id}")
        
        # Determine type
        item_type = media.get('format', '')
        
        # Extract external IDs
        external_ids = self.extract_external_ids(media)
        
        # Build metadata
        metadata = {
            "titles": title_data,
            "format": media.get('format'),
            "status": media.get('status'),
            "episodes": media.get('episodes'),
            "start_date": media.get('startDate'),
            "end_date": media.get('endDate'),
            "season": media.get('season'),
            "season_year": media.get('seasonYear'),
            "source": media.get('source'),
            "country": media.get('countryOfOrigin')
        }
        
        return self.format_item(
            item_id=anilist_id,
            title=title,
            item_type=item_type,
            external_ids=external_ids,
            metadata=metadata
        )
    
    def extract_external_ids(self, media: Dict[str, Any]) -> Dict[str, str]:
        """Extract external IDs from AniList media"""
        ids = {
            'anilist': str(media['id'])
        }
        
        # MAL ID
        if media.get('idMal'):
            ids['mal'] = str(media['idMal'])
        
        # Parse external links
        for link in media.get('externalLinks', []):
            site = link.get('site', '').lower()
            url = link.get('url', '')
            
            if not url:
                continue
            
            try:
                if 'kitsu' in site:
                    # Extract kitsu ID from URL
                    match = re.search(r'/anime/(\d+)', url) or re.search(r'/anime/([^/?]+)', url)
                    if match:
                        ids['kitsu'] = match.group(1)
                
                elif 'anidb' in site:
                    # Extract anidb ID from URL
                    match = re.search(r'aid=(\d+)', url) or re.search(r'/anime/(\d+)', url)
                    if match:
                        ids['anidb'] = match.group(1)
                
                elif 'thetvdb' in site or 'tvdb' in site:
                    match = re.search(r'/series/(\d+)', url) or re.search(r'id=(\d+)', url)
                    if match:
                        ids['tvdb'] = match.group(1)
                
                elif 'themoviedb' in site or 'tmdb' in site:
                    match = re.search(r'/tv/(\d+)', url) or re.search(r'/movie/(\d+)', url)
                    if match:
                        ids['themoviedb'] = match.group(1)
                
                elif 'imdb' in site:
                    match = re.search(r'(tt\d+)', url)
                    if match:
                        ids['imdb'] = match.group(1)
                
                elif 'anime-planet' in site or 'animeplanet' in site:
                    match = re.search(r'/anime/([^/?]+)', url)
                    if match:
                        ids['animeplanet'] = match.group(1)
                
                elif 'animenewsnetwork' in site or 'ann' in site:
                    match = re.search(r'id=(\d+)', url)
                    if match:
                        ids['animenewsnetwork'] = match.group(1)
                
                elif 'livechart' in site:
                    match = re.search(r'/anime/(\d+)', url)
                    if match:
                        ids['livechart'] = match.group(1)
                
            except Exception as e:
                continue
        
        return ids
