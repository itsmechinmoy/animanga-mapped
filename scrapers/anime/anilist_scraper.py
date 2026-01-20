"""
AniList scraper for both anime and manga
"""
from typing import Dict, List, Any
from scrapers.base_scraper import BaseScraper
import re

class AniListScraper(BaseScraper):
    """Scraper for AniList API"""
    
    API_URL = "https://graphql.anilist.co"
    
    QUERY = """
    query ($page: Int, $type: MediaType) {
      Page(page: $page, perPage: 50) {
        pageInfo { hasNextPage currentPage lastPage }
        media(type: $type, sort: ID) {
          id idMal format status episodes chapters volumes
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
    
    def __init__(self, media_type: str = "anime"):
        """
        Args:
            media_type: "anime" or "manga"
        """
        super().__init__("anilist", media_type)
        self.media_type_upper = media_type.upper()
    
    def get_rate_limit(self) -> float:
        return 1.0  # 1 second between requests
    
    def scrape(self) -> List[Dict[str, Any]]:
        """Scrape AniList data"""
        results = []
        page = self.checkpoint.get("page", 1)
        
        print(f"Starting from page {page}...")
        
        while True:
            try:
                response = self.session.post(
                    self.API_URL,
                    json={
                        'query': self.QUERY,
                        'variables': {
                            'page': page,
                            'type': self.media_type_upper
                        }
                    }
                )
                
                data = response.json()
                
                if 'errors' in data:
                    print(f"  [ERROR] GraphQL errors: {data['errors']}")
                    break
                
                page_data = data.get('data', {}).get('Page', {})
                media_list = page_data.get('media', [])
                page_info = page_data.get('pageInfo', {})
                
                if not media_list:
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
                    break
                
                page += 1
                
            except Exception as e:
                print(f"  [ERROR] Page {page} failed: {e}")
                break
        
        return results
    
    def process_media(self, media: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single media item"""
        anilist_id = media['id']
        title = media['title']['romaji'] or media['title']['english'] or media['title']['native']
        
        # Determine type
        item_type = media.get('format', '')
        
        # Extract external IDs
        external_ids = self.extract_external_ids(media)
        
        # Build metadata
        metadata = {
            "titles": media['title'],
            "format": media.get('format'),
            "status": media.get('status'),
            "episodes": media.get('episodes'),
            "chapters": media.get('chapters'),
            "volumes": media.get('volumes'),
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
            
            if 'kitsu' in site:
                # Extract kitsu ID from URL
                match = re.search(r'/anime/(\d+)', url) or re.search(r'/manga/(\d+)', url)
                if match:
                    ids['kitsu'] = match.group(1)
            
            elif 'anidb' in site:
                # Extract anidb ID from URL
                match = re.search(r'aid=(\d+)', url) or re.search(r'/anime/(\d+)', url)
                if match:
                    ids['anidb'] = match.group(1)
            
            elif 'thetvdb' in site or 'tvdb' in site:
                match = re.search(r'/series/(\d+)', url)
                if match:
                    ids['tvdb'] = match.group(1)
            
            elif 'themoviedb' in site or 'tmdb' in site:
                match = re.search(r'/tv/(\d+)', url) or re.search(r'/movie/(\d+)', url)
                if match:
                    ids['themoviedb'] = match.group(1)
        
        return ids
