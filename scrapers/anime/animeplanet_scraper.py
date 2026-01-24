"""
Anime-Planet scraper (Advanced: Rotates Browser Fingerprints to bypass 403/429)
File: scrapers/anime/animeplanet_scraper.py
"""
from typing import Dict, List, Any
import sys
import time
import random
from pathlib import Path
from bs4 import BeautifulSoup
import re
from curl_cffi import requests as cffi_requests

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scrapers.base_scraper import BaseScraper

class AnimePlanetScraper(BaseScraper):
    """Scraper for Anime-Planet using Rotating TLS Fingerprints"""
    
    BASE_URL = "https://www.anime-planet.com"
    BROWSE_URL = f"{BASE_URL}/anime/all"
    
    # List of valid browser signatures to rotate through
    # This tricks Cloudflare into thinking we are different users/browsers
    BROWSER_ROTATION = [
        "chrome110", "chrome119", "chrome120", 
        "safari15_3", "safari15_5", "edge101"
    ]
    
    def __init__(self):
        super().__init__("animeplanet", "anime")
        self.session = None
        self.current_browser = "chrome120"
    
    def get_rate_limit(self) -> float:
        # A bit slower to be safe
        return 6.0 
    
    def get_new_session(self):
        """Creates a new session with a random browser fingerprint"""
        self.current_browser = random.choice(self.BROWSER_ROTATION)
        # print(f"  [i] Switching fingerprint to: {self.current_browser}")
        return cffi_requests.Session(impersonate=self.current_browser)

    def scrape(self) -> List[Dict[str, Any]]:
        print("Starting Anime-Planet scrape with Rotating TLS...")
        
        results = []
        page = self.checkpoint.get("page", 1)
        max_pages = 760 
        
        # Initialize first session
        self.session = self.get_new_session()
        
        consecutive_errors = 0
        
        while page <= max_pages:
            try:
                url = f"{self.BROWSE_URL}?page={page}"
                print(f"  Page {page}/{max_pages} [{self.current_browser}]...", end="\r")
                
                # Request with timeout
                try:
                    response = self.session.get(url, timeout=30)
                except Exception as e:
                    print(f"\n  [!] Connection error: {e}")
                    consecutive_errors += 1
                    time.sleep(10)
                    self.session = self.get_new_session()
                    continue

                # --- HANDLING BLOCKS (403 / 429) ---
                if response.status_code in [403, 429, 503]:
                    consecutive_errors += 1
                    wait_time = (random.randint(10, 30) * consecutive_errors)
                    
                    err_name = "Cloudflare Block" if response.status_code == 403 else "Rate Limit"
                    print(f"\n  [!] {err_name} ({response.status_code}). Rotating ID & Sleeping {wait_time}s...")
                    
                    time.sleep(wait_time)
                    
                    # ROTATE FINGERPRINT
                    self.session = self.get_new_session()
                    
                    if consecutive_errors > 10:
                        print("\n  [!] Too many consecutive blocks. Stopping to protect IP.")
                        break
                    
                    # Retry the same page
                    continue
                
                # Check for other non-200 errors
                if response.status_code != 200:
                    print(f"\n  [!] HTTP {response.status_code} - Skipping page")
                    page += 1
                    continue

                # Reset error counter on success
                consecutive_errors = 0
                
                # --- PARSING ---
                soup = BeautifulSoup(response.content, 'html.parser')
                cards = soup.select('li.card')
                
                if not cards:
                    # Sometimes Cloudflare returns 200 but with a captcha page
                    if "challenge" in soup.text.lower() or "cloudflare" in soup.text.lower():
                        print("\n  [!] Soft Block (Captcha). Rotating ID...")
                        self.session = self.get_new_session()
                        time.sleep(15)
                        continue
                        
                    print(f"\n  [!] No cards found on page {page}. Likely end of list.")
                    break
                
                page_results = 0
                for card in cards:
                    try:
                        processed = self.process_card(card)
                        if processed:
                            results.append(processed)
                            page_results += 1
                    except Exception:
                        continue
                
                print(f"  Page {page}: Extracted {page_results} items ({self.current_browser})")
                
                # Save checkpoint
                self.checkpoint['page'] = page + 1
                self.save_checkpoint(self.checkpoint)
                page += 1
                
                # Check next link
                next_link = soup.select_one('li.next a')
                if not next_link:
                    print("\n  Reached last page.")
                    break
                    
                # Jitter sleep
                time.sleep(random.uniform(3.0, 7.0))

            except KeyboardInterrupt:
                print("\n  [!] Scrape interrupted by user.")
                break
            except Exception as e:
                print(f"\n  [ERROR] Critical failure on page {page}: {e}")
                break
        
        print(f"\n✓ Scrape complete. Total items in this run: {len(results)}")
        return results
    
    def process_card(self, card: BeautifulSoup) -> Dict[str, Any]:
        """Process an anime card element using the 'Tooltip' strategy"""
        ap_id = card.get('data-id')
        
        link_tag = card.select_one('a.tooltip')
        if not link_tag:
            return None
            
        href = link_tag.get('href', '')
        slug = href.replace('/anime/', '').strip('/')
        
        tooltip_html = link_tag.get('title', '')
        if not tooltip_html:
            return None
            
        meta_soup = BeautifulSoup(tooltip_html, 'html.parser')
        
        title_tag = meta_soup.find('h5', class_='theme-font')
        title = title_tag.get_text(strip=True) if title_tag else slug
        
        alt_title = None
        alt_tag = meta_soup.find('h6', class_='tooltip-alt')
        if alt_tag:
            alt_text = alt_tag.get_text(strip=True)
            if "Alt title:" in alt_text:
                alt_title = alt_text.replace("Alt title:", "").strip()

        item_type = "Unknown"
        episodes = None
        type_tag = meta_soup.select_one('.entryBar .type')
        if type_tag:
            type_text = type_tag.get_text(strip=True)
            match = re.match(r'([^(]+)(?:\(([^)]+)\))?', type_text)
            if match:
                item_type = match.group(1).strip()
                if match.group(2):
                    ep_text = match.group(2)
                    ep_match = re.search(r'(\d+)', ep_text)
                    if ep_match:
                        episodes = int(ep_match.group(1))

        year = None
        year_tag = meta_soup.select_one('.entryBar .iconYear')
        if year_tag:
            year_text = year_tag.get_text(strip=True)
            if '-' in year_text:
                year = year_text.split('-')[0].strip()
            else:
                year = year_text.strip()
            if year.isdigit():
                year = int(year)

        tags = []
        tag_list = meta_soup.select('.tags li')
        for tag in tag_list:
            tags.append(tag.get_text(strip=True))

        external_ids = {
            'animeplanet': slug,
            'animeplanet_id': ap_id
        }
        
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
