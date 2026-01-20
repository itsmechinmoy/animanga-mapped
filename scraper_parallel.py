"""
Parallel Scraper for Anime/Manga Database
Scrapes one service at a time (called by GitHub Actions matrix)
Each service extracts ID mappings to other services where available
Supports: AniList, MAL (via Jikan), Kitsu, SIMKL
"""

import requests
import time
import json
import os
from pathlib import Path
import re

# ============================================================================
# CONFIGURATION
# ============================================================================
BASE_DIR = Path("media_database")
TARGET_SERVICE = os.getenv("TARGET_SERVICE", "anilist-anime")  # e.g., "anilist-anime"
SCRAPE_MODE = os.getenv("SCRAPE_MODE", "update")  # "full" or "update"
SIMKL_CLIENT_ID = os.getenv("SIMKL_CLIENT_ID")

# Parse target service and media type
service_name, media_type = TARGET_SERVICE.split('-')
CHECKPOINT_FILE = Path(f"checkpoint_{TARGET_SERVICE}.json")

# API Endpoints
ANILIST_API = "https://graphql.anilist.co"
JIKAN_API = "https://api.jikan.moe/v4"
KITSU_API = "https://kitsu.io/api/edge"
SIMKL_API = "https://api.simkl.com"

# Rate Limits (seconds between requests)
RATE_LIMITS = {
    "anilist": 1.0,
    "mal": 1.0,
    "kitsu": 0.5,
    "simkl": 0.5
}

class ParallelScraper:
    """Scraper for a single service (runs in parallel with other services)"""
    
    def __init__(self):
        self.service = service_name
        self.media_type = media_type
        self.mode = SCRAPE_MODE
        self.checkpoint = self.load_checkpoint()
        self.stats = {
            "service": self.service,
            "media_type": self.media_type,
            "mode": self.mode,
            "start_time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "items_processed": 0,
            "new_items": 0,
            "updated_items": 0
        }
        
        # Create output directory for this service
        self.output_dir = BASE_DIR / TARGET_SERVICE
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"\n{'='*70}")
        print(f"SCRAPING: {service_name.upper()} - {media_type.upper()}")
        print(f"MODE: {self.mode.upper()}")
        print(f"OUTPUT: {self.output_dir}")
        print(f"{'='*70}\n")
    
    def load_checkpoint(self):
        """Load checkpoint from previous run"""
        if CHECKPOINT_FILE.exists():
            with open(CHECKPOINT_FILE, 'r') as f:
                return json.load(f)
        return {"page": 1, "offset": 0}
    
    def save_checkpoint(self):
        """Save checkpoint and stats"""
        with open(CHECKPOINT_FILE, 'w') as f:
            json.dump(self.checkpoint, f, indent=2)
        
        # Save stats
        self.stats["end_time"] = time.strftime("%Y-%m-%d %H:%M:%S")
        stats_file = self.output_dir / "stats.json"
        with open(stats_file, 'w') as f:
            json.dump(self.stats, f, indent=2)
    
    def save_media(self, media_id, data, mappings):
        """Save media data with ID mappings to other services"""
        filepath = self.output_dir / f"{media_id}.json"
        
        # Check if this is new or updated
        if self.mode == "update" and filepath.exists():
            file_age = time.time() - filepath.stat().st_mtime
            if file_age < 7 * 24 * 3600:  # Less than 7 days old
                return  # Skip, file is recent
            self.stats["updated_items"] += 1
        else:
            self.stats["new_items"] += 1
        
        record = {
            "service": self.service,
            "media_id": str(media_id),
            "media_type": self.media_type,
            "id_mappings": mappings,  # Cross-references to other services
            "data": data,  # Full data from THIS service
            "last_updated": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(record, f, indent=2, ensure_ascii=False)
        
        self.stats["items_processed"] += 1
    
    # ========================================================================
    # ANILIST SCRAPER
    # ========================================================================
    def scrape_anilist(self):
        """Scrape AniList database - provides MAL IDs and external links"""
        page = self.checkpoint["page"]
        
        query = """
        query ($page: Int, $type: MediaType) {
          Page(page: $page, perPage: 50) {
            pageInfo { hasNextPage lastPage currentPage }
            media(type: $type, sort: ID) {
              id idMal format status episodes chapters volumes
              title { romaji english native }
              description
              startDate { year month day }
              endDate { year month day }
              season seasonYear coverImage { extraLarge large }
              bannerImage genres tags { name rank }
              averageScore meanScore popularity favourites
              source countryOfOrigin
              studios { nodes { name isAnimationStudio } }
              staff { edges { role node { name { full native } } } }
              characters { edges { role voiceActors { name { full } language } node { name { full } } } }
              relations { edges { relationType node { id type } } }
              externalLinks { url site }
              streamingEpisodes { title thumbnail url }
              rankings { rank type context }
              trailer { id site }
            }
          }
        }
        """
        
        while True:
            try:
                r = requests.post(ANILIST_API, json={
                    'query': query,
                    'variables': {'page': page, 'type': self.media_type.upper()}
                }, timeout=20)
                data = r.json().get('data', {}).get('Page', {})
            except Exception as e:
                print(f"[ERROR] {e}. Retrying in 10s...")
                time.sleep(10)
                continue
            
            if not data or not data.get('media'):
                break
            
            media_list = data['media']
            info = data['pageInfo']
            print(f"Page {info['currentPage']}/{info['lastPage']} - {len(media_list)} items")
            
            for media in media_list:
                al_id = media['id']
                
                # Extract ID mappings from AniList data
                mappings = {
                    "anilist": str(al_id),
                    "mal": str(media.get('idMal', '')) if media.get('idMal') else '',
                    "kitsu": "",
                    "anidb": "",
                    "simkl": "",
                    "tmdb": "",
                    "imdb": ""
                }
                
                # Parse external links for other service IDs
                for link in media.get('externalLinks', []):
                    site = link['site'].lower()
                    url = link['url']
                    
                    if "kitsu" in site:
                        mappings["kitsu"] = url.rstrip('/').split('/')[-1]
                    elif "anidb" in site:
                        if '=' in url:
                            mappings["anidb"] = url.split('=')[-1]
                        else:
                            mappings["anidb"] = url.rstrip('/').split('/')[-1]
                
                self.save_media(al_id, media, mappings)
                title = media['title']['romaji'][:50]
                print(f"  ✓ {al_id}: {title}")
            
            self.checkpoint["page"] = page
            self.save_checkpoint()
            
            if not info['hasNextPage']:
                break
            
            page += 1
            time.sleep(RATE_LIMITS["anilist"])
        
        print(f"\n✓✓✓ AniList {self.media_type} complete!")
    
    # ========================================================================
    # MAL SCRAPER (via Jikan API)
    # ========================================================================
    def scrape_mal(self):
        """Scrape MyAnimeList via Jikan API - provides AniList and AniDB links"""
        page = self.checkpoint["page"]
        
        while True:
            try:
                # Get page of items
                r = requests.get(
                    f"{JIKAN_API}/{self.media_type}?page={page}&limit=25",
                    timeout=15
                )
                
                if r.status_code == 429:  # Rate limited
                    print("[RATE LIMIT] Waiting 60s...")
                    time.sleep(60)
                    continue
                
                data = r.json()
                if 'data' not in data or not data['data']:
                    break
                
                items = data['data']
                pagination = data.get('pagination', {})
                print(f"Page {page}/{pagination.get('last_visible_page', '?')} - {len(items)} items")
                
                for item in items:
                    mal_id = item['mal_id']
                    
                    # Get full details for this item
                    try:
                        detail_r = requests.get(
                            f"{JIKAN_API}/{self.media_type}/{mal_id}/full",
                            timeout=15
                        )
                        time.sleep(RATE_LIMITS["mal"])
                        
                        if detail_r.status_code == 200:
                            full_data = detail_r.json().get('data', {})
                        else:
                            full_data = item
                    except:
                        full_data = item
                    
                    # Build ID mappings
                    mappings = {
                        "mal": str(mal_id),
                        "anilist": "",
                        "kitsu": "",
                        "anidb": "",
                        "simkl": "",
                        "tmdb": "",
                        "imdb": ""
                    }
                    
                    # Parse external links
                    externals = full_data.get('external', [])
                    for ext in externals:
                        url = ext.get('url', '').lower()
                        
                        if 'anilist.co' in url:
                            mappings["anilist"] = url.rstrip('/').split('/')[-1]
                        elif 'anidb.net' in url:
                            match = re.search(r'aid=(\d+)', url)
                            if match:
                                mappings["anidb"] = match.group(1)
                    
                    self.save_media(mal_id, full_data, mappings)
                    title = full_data.get('title', 'Unknown')[:50]
                    print(f"  ✓ {mal_id}: {title}")
                
                self.checkpoint["page"] = page
                self.save_checkpoint()
                
                if not pagination.get('has_next_page'):
                    break
                
                page += 1
                time.sleep(RATE_LIMITS["mal"])
                
            except Exception as e:
                print(f"[ERROR] {e}. Retrying in 10s...")
                time.sleep(10)
        
        print(f"\n✓✓✓ MAL {self.media_type} complete!")
    
    # ========================================================================
    # KITSU SCRAPER
    # ========================================================================
    def scrape_kitsu(self):
        """Scrape Kitsu database - usually doesn't provide external IDs"""
        offset = self.checkpoint["offset"]
        limit = 20
        
        headers = {
            "Accept": "application/vnd.api+json",
            "Content-Type": "application/vnd.api+json"
        }
        
        while True:
            try:
                r = requests.get(
                    f"{KITSU_API}/{self.media_type}?page[limit]={limit}&page[offset]={offset}",
                    headers=headers,
                    timeout=15
                )
                
                if r.status_code != 200:
                    print(f"[ERROR] Status {r.status_code}. Stopping.")
                    break
                
                data = r.json()
                items = data.get('data', [])
                
                if not items:
                    break
                
                print(f"Offset {offset} - {len(items)} items")
                
                for item in items:
                    kitsu_id = item['id']
                    
                    # Kitsu usually doesn't provide external IDs
                    mappings = {
                        "kitsu": str(kitsu_id),
                        "anilist": "",
                        "mal": "",
                        "anidb": "",
                        "simkl": "",
                        "tmdb": "",
                        "imdb": ""
                    }
                    
                    self.save_media(kitsu_id, item, mappings)
                    
                    attrs = item.get('attributes', {})
                    title = attrs.get('canonicalTitle', 'Unknown')[:50]
                    print(f"  ✓ {kitsu_id}: {title}")
                
                self.checkpoint["offset"] = offset
                self.save_checkpoint()
                
                offset += limit
                time.sleep(RATE_LIMITS["kitsu"])
                
            except Exception as e:
                print(f"[ERROR] {e}. Retrying in 10s...")
                time.sleep(10)
        
        print(f"\n✓✓✓ Kitsu {self.media_type} complete!")
    
    # ========================================================================
    # SIMKL SCRAPER
    # ========================================================================
    def scrape_simkl(self):
        """Scrape Simkl database using search and trending endpoints"""
        if not SIMKL_CLIENT_ID:
            print("[ERROR] SIMKL_CLIENT_ID not found. Skipping SIMKL scrape.")
            return
        
        headers = {"simkl-api-key": SIMKL_CLIENT_ID}
        
        # Simkl uses different media types: "anime" or "tv"
        simkl_type = self.media_type  # anime or tv
        
        print(f"Scraping SIMKL {simkl_type}...")
        
        # Strategy: Use trending/popular endpoints and search by year
        all_simkl_ids = set()
        
        # 1. Get trending/popular/best lists
        print("Fetching trending, popular, and best lists...")
        endpoints = [
            f"{SIMKL_API}/{simkl_type}/trending",
            f"{SIMKL_API}/{simkl_type}/popular",
            f"{SIMKL_API}/{simkl_type}/best"
        ]
        
        for endpoint in endpoints:
            try:
                r = requests.get(endpoint, headers=headers, timeout=15)
                if r.status_code == 200:
                    items = r.json()
                    for item in items[:100]:  # Top 100 from each list
                        simkl_id = item.get('ids', {}).get('simkl')
                        if simkl_id:
                            all_simkl_ids.add(simkl_id)
                    print(f"  Loaded {len(items[:100])} from {endpoint.split('/')[-1]}")
                time.sleep(RATE_LIMITS["simkl"])
            except Exception as e:
                print(f"[ERROR] {endpoint}: {e}")
        
        # 2. Search by year (2000-2025)
        print("Searching by year (2000-2025)...")
        for year in range(2000, 2026):
            try:
                r = requests.get(
                    f"{SIMKL_API}/search/{simkl_type}",
                    params={"year": year, "limit": 50},
                    headers=headers,
                    timeout=15
                )
                if r.status_code == 200:
                    results = r.json()
                    for item in results:
                        simkl_id = item.get('ids', {}).get('simkl')
                        if simkl_id:
                            all_simkl_ids.add(simkl_id)
                    if year % 5 == 0:
                        print(f"  Processed up to year {year}...")
                time.sleep(RATE_LIMITS["simkl"])
            except Exception as e:
                print(f"[ERROR] Year {year}: {e}")
        
        print(f"\n✓ Found {len(all_simkl_ids)} unique Simkl IDs")
        print("Fetching full details for each item...\n")
        
        # 3. Fetch full details for each ID
        for idx, simkl_id in enumerate(sorted(all_simkl_ids), 1):
            try:
                # Get full item details
                r = requests.get(
                    f"{SIMKL_API}/{simkl_type}/{simkl_id}",
                    headers=headers,
                    timeout=15
                )
                
                if r.status_code != 200:
                    continue
                
                full_data = r.json()
                
                # Extract ID mappings from Simkl's IDs object
                # SIMKL provides excellent cross-references!
                ids = full_data.get('ids', {})
                mappings = {
                    "simkl": str(simkl_id),
                    "mal": str(ids.get('mal', '')) if ids.get('mal') else '',
                    "anilist": str(ids.get('anilist', '')) if ids.get('anilist') else '',
                    "anidb": str(ids.get('anidb', '')) if ids.get('anidb') else '',
                    "kitsu": "",  # Simkl doesn't provide Kitsu IDs
                    "tmdb": str(ids.get('tmdb', '')) if ids.get('tmdb') else '',
                    "imdb": str(ids.get('imdb', '')) if ids.get('imdb') else ''
                }
                
                self.save_media(simkl_id, full_data, mappings)
                
                title = full_data.get('title', 'Unknown')[:50]
                print(f"  ✓ [{idx}/{len(all_simkl_ids)}] Simkl {simkl_id}: {title}")
                
                time.sleep(RATE_LIMITS["simkl"])
                
            except Exception as e:
                print(f"[ERROR] Simkl ID {simkl_id}: {e}")
        
        print(f"\n✓✓✓ Simkl {simkl_type} complete!")
    
    # ========================================================================
    # MAIN EXECUTION
    # ========================================================================
    def run(self):
        """Run the appropriate scraper based on service"""
        if self.service == "anilist":
            self.scrape_anilist()
        elif self.service == "mal":
            self.scrape_mal()
        elif self.service == "kitsu":
            self.scrape_kitsu()
        elif self.service == "simkl":
            self.scrape_simkl()
        else:
            print(f"[ERROR] Unknown service: {self.service}")
            return
        
        self.save_checkpoint()
        
        print(f"\n{'='*70}")
        print(f"COMPLETE: {self.service.upper()} - {self.media_type.upper()}")
        print(f"Items processed: {self.stats['items_processed']}")
        print(f"New: {self.stats['new_items']} | Updated: {self.stats['updated_items']}")
        print(f"{'='*70}\n")

if __name__ == "__main__":
    scraper = ParallelScraper()
    scraper.run()
