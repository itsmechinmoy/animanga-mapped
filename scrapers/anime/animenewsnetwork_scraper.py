"""
AnimeNewsNetwork scraper
File: scrapers/anime/animenewsnetwork_scraper.py
"""
from typing import Dict, List, Any
import sys
from pathlib import Path
import xml.etree.ElementTree as ET
import time

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scrapers.base_scraper import BaseScraper

class AnimeNewsNetworkScraper(BaseScraper):
    """Scraper for AnimeNewsNetwork API"""
    
    # ANN uses XML API
    API_URL = "https://cdn.animenewsnetwork.com/encyclopedia/api.xml"
    REPORTS_URL = "https://www.animenewsnetwork.com/encyclopedia/reports.xml"
    
    def __init__(self):
        super().__init__("animenewsnetwork", "anime")
    
    def get_rate_limit(self) -> float:
        return 2.0  # 2 seconds - ANN has strict rate limits
    
    def scrape(self) -> List[Dict[str, Any]]:
        """
        Scrape ANN data
        ANN API is limited and doesn't provide a full list endpoint
        We'll use the reports.xml which gives us a list of anime IDs
        """
        print("Fetching anime list from ANN reports...")
        print("This may take a long time due to rate limits (2s per request)\n")
        
        results = []
        
        try:
            # Get the list of anime from reports
            print("Step 1: Fetching anime ID list...")
            response = self.session.get(
                f"{self.REPORTS_URL}?id=155&type=anime&nlist=all"
            )
            
            if response.status_code != 200:
                print(f"[!] Failed to fetch ANN reports: {response.status_code}")
                return results
            
            # Parse the XML
            print("Step 2: Parsing XML response...")
            root = ET.fromstring(response.content)
            
            # Extract all anime items
            items = root.findall('.//item')
            total = len(items)
            print(f"✓ Found {total} anime IDs in reports\n")
            
            print("Step 3: Fetching details for each anime...")
            print("Note: Rate limited to 1 request per 2 seconds\n")
            
            last_id = self.checkpoint.get("last_id", 0)
            processed_count = 0
            
            for idx, item in enumerate(items, 1):
                try:
                    ann_id_elem = item.find('id')
                    if ann_id_elem is None:
                        continue
                    
                    ann_id = int(ann_id_elem.text)
                    
                    # Skip if we've already processed this
                    if ann_id <= last_id:
                        continue
                    
                    # Get details for this anime
                    processed = self.fetch_anime_details(ann_id)
                    if processed:
                        results.append(processed)
                        processed_count += 1
                    
                    # Show progress more frequently
                    if idx % 10 == 0:
                        elapsed = idx * 2  # Rough estimate
                        remaining = (total - idx) * 2
                        print(f"  [{idx}/{total}] Processed {processed_count} items | "
                              f"Elapsed: ~{elapsed//60}m | Remaining: ~{remaining//60}m")
                    
                    # Save checkpoint every 50 items
                    if idx % 50 == 0:
                        self.checkpoint['last_id'] = ann_id
                        self.save_checkpoint(self.checkpoint)
                        print(f"  ✓ Checkpoint saved at ID {ann_id}")
                    
                except Exception as e:
                    print(f"  [WARN] Failed to process item {idx}: {e}")
                    continue
            
            # Final checkpoint
            if items:
                final_id = int(items[-1].find('id').text)
                self.checkpoint['last_id'] = final_id
                self.save_checkpoint(self.checkpoint)
            
            print(f"\n✓ Processed {len(results)} items")
            return results
            
        except Exception as e:
            print(f"[ERROR] Failed to scrape ANN: {e}")
            return results
    
    def fetch_anime_details(self, ann_id: int) -> Dict[str, Any]:
        """Fetch details for a specific anime ID"""
        try:
            response = self.session.get(
                f"{self.API_URL}?anime={ann_id}"
            )
            
            if response.status_code != 200:
                return None
            
            root = ET.fromstring(response.content)
            anime = root.find('.//anime')
            
            if anime is None:
                return None
            
            # Extract title
            title_elem = anime.find('.//info[@type="Main title"]')
            title = title_elem.text if title_elem is not None else f"Unknown {ann_id}"
            
            # Extract type
            type_elem = anime.find('.//info[@type="Genres"]')
            item_type = type_elem.text if type_elem is not None else ""
            
            # Extract external IDs
            external_ids = self.extract_external_ids(anime)
            
            # Build metadata
            metadata = {
                "titles": self.extract_titles(anime),
                "type": item_type,
                "episodes": self.extract_episodes(anime),
                "vintage": self.extract_vintage(anime),
                "genres": self.extract_genres(anime),
                "themes": self.extract_themes(anime),
                "related": self.extract_related(anime)
            }
            
            return self.format_item(ann_id, title, item_type, external_ids, metadata)
            
        except Exception as e:
            return None
    
    def extract_titles(self, anime: ET.Element) -> Dict[str, str]:
        """Extract all title variants"""
        titles = {}
        
        for info in anime.findall('.//info[@type]'):
            info_type = info.get('type', '')
            if 'title' in info_type.lower():
                titles[info_type] = info.text
        
        return titles
    
    def extract_episodes(self, anime: ET.Element) -> int:
        """Extract episode count"""
        ep_elem = anime.find('.//info[@type="Number of episodes"]')
        if ep_elem is not None and ep_elem.text:
            try:
                return int(ep_elem.text)
            except:
                pass
        return None
    
    def extract_vintage(self, anime: ET.Element) -> str:
        """Extract vintage/air date"""
        vintage_elem = anime.find('.//info[@type="Vintage"]')
        return vintage_elem.text if vintage_elem is not None else None
    
    def extract_genres(self, anime: ET.Element) -> List[str]:
        """Extract genres"""
        genres = []
        for info in anime.findall('.//info[@type="Genres"]'):
            if info.text:
                genres.append(info.text)
        return genres
    
    def extract_themes(self, anime: ET.Element) -> List[str]:
        """Extract themes"""
        themes = []
        for info in anime.findall('.//info[@type="Themes"]'):
            if info.text:
                themes.append(info.text)
        return themes
    
    def extract_related(self, anime: ET.Element) -> List[Dict[str, Any]]:
        """Extract related anime"""
        related = []
        for rel in anime.findall('.//related-prev') + anime.findall('.//related-next'):
            related.append({
                'id': rel.get('id'),
                'rel': rel.get('rel')
            })
        return related
    
    def extract_external_ids(self, anime: ET.Element) -> Dict[str, str]:
        """Extract external IDs from ANN anime"""
        ids = {'animenewsnetwork': anime.get('id')}
        
        # ANN doesn't directly provide external IDs in their API
        # These would need to be cross-referenced
        
        return ids
