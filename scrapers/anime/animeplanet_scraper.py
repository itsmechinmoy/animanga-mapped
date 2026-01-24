"""
Anime-Planet scraper (Accelerated: Multithreaded with Rotating Fingerprints)
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
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scrapers.base_scraper import BaseScraper

class AnimePlanetScraper(BaseScraper):
    """Scraper for Anime-Planet using Rotating TLS Fingerprints & Multithreading"""
    
    BASE_URL = "https://www.anime-planet.com"
    BROWSE_URL = f"{BASE_URL}/anime/all"
    
    # List of valid browser signatures to rotate through
    BROWSER_ROTATION = [
        "chrome110", "chrome119", "chrome120", 
        "safari15_3", "safari15_5", "edge101"
    ]
    
    def __init__(self):
        super().__init__("animeplanet", "anime")
        self.max_workers = 4  # Running 4 concurrent browsers
    
    def get_rate_limit(self) -> float:
        return 1.0  # Per-thread limit (not global)
    
    def get_new_session(self):
        """Creates a new session with a random browser fingerprint"""
        browser = random.choice(self.BROWSER_ROTATION)
        return cffi_requests.Session(impersonate=browser), browser

    def scrape_page(self, page: int) -> List[Dict[str, Any]]:
        """Worker function to scrape a single page"""
        session, current_browser = self.get_new_session()
        consecutive_errors = 0
        page_results = []
        
        while True:
            try:
                url = f"{self.BROWSE_URL}?page={page}"
                
                # Request with timeout
                try:
                    response = session.get(url, timeout=30)
                except Exception:
                    consecutive_errors += 1
                    time.sleep(5)
                    session, current_browser = self.get_new_session()
                    continue

                # --- HANDLING BLOCKS (403 / 429) ---
                if response.status_code in [403, 429, 503]:
                    consecutive_errors += 1
                    # Exponential backoff with jitter
                    wait_time = (random.randint(5, 15) * consecutive_errors)
                    print(f"  [!] Blocked on Pg {page} ({response.status_code}). Sleeping {wait_time}s...")
                    time.sleep(wait_time)
                    
                    # Rotate Fingerprint
                    session, current_browser = self.get_new_session()
                    
                    if consecutive_errors > 5:
                        print(f"  [!] Giving up on Page {page} after 5 tries.")
                        return []
                    continue
                
                if response.status_code != 200:
                    print(f"  [!] HTTP {response.status_code} on Pg {page} - Skipping")
                    return []

                # --- PARSING ---
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Check for Soft Block (Captcha)
                if "challenge" in soup.text.lower() or "cloudflare" in soup.text.lower():
                    print(f"  [!] Soft Block (Captcha) on Pg {page}. Rotating...")
                    session, current_browser = self.get_new_session()
                    time.sleep(10)
                    continue

                cards = soup.select('li.card')
                if not cards:
                    return []
                
                for card in cards:
                    try:
                        processed = self.process_card(card)
                        if processed:
                            page_results.append(processed)
                    except Exception:
                        continue
                
                # Success!
                return page_results

            except Exception as e:
                print(f"  [ERROR] Page {page} crashed: {e}")
                return []
            finally:
                # Always close session to free resources
                try:
                    session.close()
                except:
                    pass

    def scrape(self) -> List[Dict[str, Any]]:
        print(f"Starting Anime-Planet scrape with {self.max_workers} threads...")
        
        results = []
        start_page = self.checkpoint.get("page", 1)
        # Assuming ~760 pages total based on current catalog
        # You can increase this, the scraper stops if pages return empty
        total_pages = 765 
        
        pages_to_scrape = range(start_page, total_pages + 1)
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Map pages to the scrape_page function
            future_to_page = {
                executor.submit(self.scrape_page, page): page 
                for page in pages_to_scrape
            }
            
            completed_count = 0
            for future in as_completed(future_to_page):
                page = future_to_page[future]
                try:
                    data = future.result()
                    if data:
                        results.extend(data)
                        print(f"  ✓ Page {page} done ({len(data)} items) [{completed_count+1}/{len(pages_to_scrape)}]")
                    else:
                        print(f"  x Page {page} returned no data")
                    
                    # Periodic checkpoint (every 10 pages)
                    completed_count += 1
                    if completed_count % 10 == 0:
                        # We save the highest page number we've reached as the checkpoint
                        # (Note: This is approximate since threads finish out of order, but safe enough)
                        self.checkpoint['page'] = page
                        self.save_checkpoint(self.checkpoint)
                        self.results = results # Update internal results
                        self.save_results()    # Intermediate save to disk
                        
                except Exception as e:
                    print(f"  [ERROR] Processing page {page} failed: {e}")

        print(f"\n✓ Scrape complete. Total items: {len(results)}")
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
