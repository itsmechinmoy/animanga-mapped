"""
Anime-Planet scraper (Fixed using curl_cffi, Tooltip parsing, and Rate Limit Handling)
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
    """Scraper for Anime-Planet using TLS impersonation and Tooltip parsing"""
    
    BASE_URL = "https://www.anime-planet.com"
    BROWSE_URL = f"{BASE_URL}/anime/all"
    
    def __init__(self):
        super().__init__("animeplanet", "anime")
    
    def get_rate_limit(self) -> float:
        # Increased to 5 seconds to avoid HTTP 429 errors
        return 5.0 
    
    def scrape(self) -> List[Dict[str, Any]]:
        print("Starting Anime-Planet scrape with TLS Impersonation...")
        
        results = []
        page = self.checkpoint.get("page", 1)
        max_pages = 760 
        consecutive_429s = 0
        
        # Create a curl_cffi session to mimic Chrome
        session = cffi_requests.Session(impersonate="chrome120")
        
        while page <= max_pages:
            try:
                url = f"{self.BROWSE_URL}?page={page}"
                print(f"  Page {page}/{max_pages}...", end="\r")
                
                # Use the impersonated session
                response = session.get(url, timeout=30)
                
                # --- HANDLE RATE LIMITING (429) ---
                if response.status_code == 429:
                    consecutive_429s += 1
                    # Exponential backoff: sleep longer if we keep hitting limits
                    wait_time = (60 * consecutive_429s) + random.uniform(5, 15)
                    print(f"\n  [!] HTTP 429 (Too Many Requests). Cooling down for {int(wait_time)}s... (Retry {consecutive_429s})")
                    time.sleep(wait_time)
                    
                    if consecutive_429s > 5:
                        print("\n  [!] Too many consecutive rate limits. Stopping to protect IP.")
                        break
                    
                    # Continue loop without incrementing 'page' to retry this page
                    continue
                
                # Reset 429 counter on valid response
                consecutive_429s = 0

                if response.status_code == 403:
                    print(f"\n  [!] Access Forbidden (403) on Page {page}. Cloudflare detected bot.")
                    break
                
                if response.status_code != 200:
                    print(f"\n  [!] HTTP {response.status_code}")
                    break
                
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Target the specific grid items
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
                        continue
                
                print(f"  Page {page}: Extracted {page_results} items")
                
                # Save checkpoint
                self.checkpoint['page'] = page + 1
                self.save_checkpoint(self.checkpoint)
                page += 1
                
                # Check for next button
                next_link = soup.select_one('li.next a')
                if not next_link:
                    print("\n  Reached last page.")
                    break
                    
                # Rate limiting sleep is handled by BaseScraper runner usually, 
                # but since we are overriding the loop here, we add a small jitter sleep
                time.sleep(random.uniform(2.0, 4.0))

            except Exception as e:
                print(f"\n  [ERROR] Page {page} failed: {e}")
                # Sleep a bit on crash before retry
                time.sleep(10)
                break
        
        print(f"\n✓ Scrape complete. Total items: {len(results)}")
        return results
    
    def process_card(self, card: BeautifulSoup) -> Dict[str, Any]:
        """
        Process an anime card element using the 'Tooltip' strategy
        """
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
