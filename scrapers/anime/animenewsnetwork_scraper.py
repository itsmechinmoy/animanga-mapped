"""
AnimeNewsNetwork scraper - Optimized for speed
File: scrapers/anime/animenewsnetwork_scraper.py
"""
from typing import Dict, List, Any
import sys
from pathlib import Path
import xml.etree.ElementTree as ET

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scrapers.base_scraper import BaseScraper

class AnimeNewsNetworkScraper(BaseScraper):
    """Scraper for AnimeNewsNetwork API - Optimized"""
    
    API_URL = "https://cdn.animenewsnetwork.com/encyclopedia/api.xml"
    REPORTS_URL = "https://www.animenewsnetwork.com/encyclopedia/reports.xml"
    
    def __init__(self):
        super().__init__("animenewsnetwork", "anime")
    
    def get_rate_limit(self) -> float:
        return 1.0  # Reduced from 2s to 1s
    
    def scrape(self) -> List[Dict[str, Any]]:
        """
        Scrape ANN data - BATCH MODE
        Fetches multiple IDs per request to speed up
        """
        print("Fetching anime list from ANN reports...")
        print("Using BATCH mode (multiple IDs per request)\n")
        
        results = []
        
        try:
            # Get ID list
            print("Step 1: Fetching anime ID list...")
            response = self.session.get(
                f"{self.REPORTS_URL}?id=155&type=anime&nlist=all"
            )
            
            if response.status_code != 200:
                print(f"[!] Failed: {response.status_code}")
                return results
            
            print("Step 2: Parsing XML...")
            root = ET.fromstring(response.content)
            items = root.findall('.//item')
            
            # Extract all IDs
            all_ids = []
            for item in items:
                ann_id_elem = item.find('id')
                if ann_id_elem is not None:
                    all_ids.append(int(ann_id_elem.text))
            
            total = len(all_ids)
            print(f"✓ Found {total} anime IDs\n")
            
            # Filter already processed
            last_id = self.checkpoint.get("last_id", 0)
            ids_to_process = [id for id in all_ids if id > last_id]
            
            print(f"Step 3: Fetching details in batches...")
            print(f"To process: {len(ids_to_process)} IDs")
            print(f"Batch size: 50 IDs per request\n")
            
            # Process in batches of 50
            batch_size = 50
            processed_count = 0
            
            for i in range(0, len(ids_to_process), batch_size):
                batch = ids_to_process[i:i+batch_size]
                batch_num = (i // batch_size) + 1
                total_batches = (len(ids_to_process) + batch_size - 1) // batch_size
                
                print(f"  Batch {batch_num}/{total_batches} ({len(batch)} IDs)...", end=" ")
                
                try:
                    # Fetch batch
                    ids_str = "/".join(map(str, batch))
                    url = f"{self.API_URL}?anime={ids_str}"
                    
                    response = self.session.get(url)
                    
                    if response.status_code == 200:
                        root = ET.fromstring(response.content)
                        
                        # Process each anime in batch
                        for anime in root.findall('.//anime'):
                            try:
                                item = self.process_anime(anime)
                                if item:
                                    results.append(item)
                                    processed_count += 1
                            except:
                                continue
                        
                        print(f"✓ {processed_count} items")
                    else:
                        print(f"Failed ({response.status_code})")
                    
                    # Save checkpoint after each batch
                    if batch:
                        self.checkpoint['last_id'] = max(batch)
                        self.save_checkpoint(self.checkpoint)
                    
                except Exception as e:
                    print(f"Error: {e}")
                    continue
            
            print(f"\n✓ Total processed: {len(results)} items")
            return results
            
        except Exception as e:
            print(f"[ERROR] {e}")
            return results
    
    def process_anime(self, anime: ET.Element) -> Dict[str, Any]:
        """Process anime element"""
        ann_id = anime.get('id')
        if not ann_id:
            return None
        
        # Extract title
        title_elem = anime.find('.//info[@type="Main title"]')
        title = title_elem.text if title_elem is not None else f"Unknown {ann_id}"
        
        # Extract type
        type_elem = anime.find('.//info[@type="Genres"]')
        item_type = type_elem.text if type_elem is not None else ""
        
        # Build metadata
        metadata = {
            "titles": self.extract_titles(anime),
            "episodes": self.extract_episodes(anime),
            "vintage": self.extract_vintage(anime),
        }
        
        return self.format_item(ann_id, title, item_type, {'animenewsnetwork': ann_id}, metadata)
    
    def extract_titles(self, anime: ET.Element) -> Dict[str, str]:
        """Extract titles"""
        titles = {}
        for info in anime.findall('.//info[@type]'):
            info_type = info.get('type', '')
            if 'title' in info_type.lower() and info.text:
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
        """Extract vintage"""
        vintage_elem = anime.find('.//info[@type="Vintage"]')
        return vintage_elem.text if vintage_elem is not None else None
    
    def extract_external_ids(self, anime: ET.Element) -> Dict[str, str]:
        """Extract external IDs"""
        return {'animenewsnetwork': anime.get('id')}
