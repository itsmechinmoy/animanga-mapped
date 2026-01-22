"""
Anime-Planet scraper (Fixed using curl_cffi and Tooltip parsing)
File: scrapers/anime/animeplanet_scraper.py
"""
from typing import Dict, List, Any
import sys
from pathlib import Path
from bs4 import BeautifulSoup
import re
from curl_cffi import requests as cffi_requests  # REQUIRED: pip install curl-cffi

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scrapers.base_scraper import BaseScraper

class AnimePlanetScraper(BaseScraper):
    """Scraper for Anime-Planet using TLS impersonation and Tooltip parsing"""
    
    BASE_URL = "https://www.anime-planet.com"
    BROWSE_URL = f"{BASE_URL}/anime/all"
    
    def __init__(self):
        super().__init__("animeplanet", "anime")
        # We generally ignore the BaseScraper session for the actual requests
        # because we need curl_cffi to bypass the 403 block.
    
    def get_rate_limit(self) -> float:
        return 2.0 
    
    def scrape(self) -> List[Dict[str, Any]]:
        print("Starting Anime-Planet scrape with TLS Impersonation...")
        
        results = []
        page = self.checkpoint.get("page", 1)
        max_pages = 760 # Approx max pages based on your data
        
        # Create a curl_cffi session to mimic Chrome
        # This is the "Magic" that fixes the 403 Forbidden error
        session = cffi_requests.Session(impersonate="chrome120")
        
        while page <= max_pages:
            try:
                url = f"{self.BROWSE_URL}?page={page}"
                print(f"  Page {page}/{max_pages}...", end="\r")
                
                # Use the impersonated session
                response = session.get(url, timeout=30)
                
                if response.status_code == 403:
                    print(f"\n  [!] Still getting 403 on Page {page}. Cloudflare is tough.")
                    print("  [!] Try increasing the 'get_rate_limit' or changing impersonate version.")
                    break
                
                if response.status_code != 200:
                    print(f"\n  [!] HTTP {response.status_code}")
                    break
                
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Target the specific grid items based on view-source
                # Container: ul.cardDeck.cardGrid -> li.card
                cards = soup.select('li.card')
                
                if not cards:
                    print(f"\n  [!] No cards found on page {page}. Structure changed or end reached.")
                    break
                
                page_results = 0
                for card in cards:
                    try:
                        processed = self.process_card(card)
                        if processed:
                            results.append(processed)
                            page_results += 1
                    except Exception as e:
                        # Silently skip failed cards to keep momentum
                        continue
                
                print(f"  Page {page}: Extracted {page_results} items")
                
                # Save checkpoint
                self.checkpoint['page'] = page + 1
                self.save_checkpoint(self.checkpoint)
                page += 1
                
                # Check for next button to determine if we are done
                next_link = soup.select_one('li.next a')
                if not next_link:
                    print("\n  Reached last page.")
                    break
                    
            except Exception as e:
                print(f"\n  [ERROR] Page {page} failed: {e}")
                break
        
        print(f"\n✓ Scrape complete. Total items: {len(results)}")
        return results
    
    def process_card(self, card: BeautifulSoup) -> Dict[str, Any]:
        """
        Process an anime card element using the 'Tooltip' strategy
        found in the Java AP4J code.
        """
        # 1. Basic Data from LI attributes
        # <li data-id="12345" ...>
        ap_id = card.get('data-id')
        
        # 2. Extract Link and Slug
        link_tag = card.select_one('a.tooltip')
        if not link_tag:
            return None
            
        href = link_tag.get('href', '')
        # slug is usually the part after /anime/
        slug = href.replace('/anime/', '').strip('/')
        
        # 3. PARSE THE TOOLTIP HTML
        # The 'title' attribute contains encoded HTML. We parse it as a new soup.
        # Reference: AnimeSearchers.java line 305
        tooltip_html = link_tag.get('title', '')
        if not tooltip_html:
            return None
            
        # Parse the inner HTML of the tooltip
        meta_soup = BeautifulSoup(tooltip_html, 'html.parser')
        
        # --- Extraction Logic based on AP4J and view-source ---
        
        # Title: <h5 class='theme-font'>Title</h5>
        title_tag = meta_soup.find('h5', class_='theme-font')
        title = title_tag.get_text(strip=True) if title_tag else slug
        
        # Alt Title: <h6 class='theme-font tooltip-alt'>Alt title: ...</h6>
        alt_title = None
        alt_tag = meta_soup.find('h6', class_='tooltip-alt')
        if alt_tag:
            alt_text = alt_tag.get_text(strip=True)
            if "Alt title:" in alt_text:
                alt_title = alt_text.replace("Alt title:", "").strip()

        # Type and Episodes: <li class='type'>TV (12 eps)</li>
        item_type = "Unknown"
        episodes = None
        type_tag = meta_soup.select_one('.entryBar .type')
        if type_tag:
            type_text = type_tag.get_text(strip=True)
            # Regex to split "TV (12 eps)" or "Movie (1 ep)"
            # Java logic: Parsers.java line 18
            match = re.match(r'([^(]+)(?:\(([^)]+)\))?', type_text)
            if match:
                item_type = match.group(1).strip()
                if match.group(2):
                    ep_text = match.group(2)
                    # Extract number from "12 eps"
                    ep_match = re.search(r'(\d+)', ep_text)
                    if ep_match:
                        episodes = int(ep_match.group(1))

        # Year: <li class='iconYear'>2016</li>
        year = None
        year_tag = meta_soup.select_one('.entryBar .iconYear')
        if year_tag:
            year_text = year_tag.get_text(strip=True)
            # Handle ranges like "2016 - 2017" or single years "2016"
            if '-' in year_text:
                year = year_text.split('-')[0].strip()
            else:
                year = year_text.strip()
            
            # Simple integer conversion attempt
            if year.isdigit():
                year = int(year)

        # Tags: <div class='tags'><ul><li>Action</li>...</ul></div>
        tags = []
        tag_list = meta_soup.select('.tags li')
        for tag in tag_list:
            tags.append(tag.get_text(strip=True))

        # External IDs
        external_ids = {
            'animeplanet': slug,
            'animeplanet_id': ap_id
        }
        
        # Metadata
        metadata = {
            "slug": slug,
            "url": f"{self.BASE_URL}{href}",
            "type": item_type,
            "episodes": episodes,
            "year": year,
            "alt_title": alt_title,
            "tags": tags,
            "image_url": card.select_one('img').get('data-src') if card.select_one('img') else None
        }
        
        return self.format_item(slug, title, item_type, external_ids, metadata)
    
    def extract_external_ids(self, item: Dict[str, Any]) -> Dict[str, str]:
        return {'animeplanet': item.get('slug', '')}
