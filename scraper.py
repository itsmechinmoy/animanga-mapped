import requests
import time
import json
from pathlib import Path
from bs4 import BeautifulSoup
import re
from collections import defaultdict

# ============================================================================
# CONFIGURATION
# ============================================================================
import os

BASE_DIR = Path("media_database")
CHECKPOINT_FILE = Path("scraper_checkpoint.json")
MAPPING_DB = Path("cross_reference.json")
STATS_FILE = BASE_DIR / "stats.json"

# Get API key from environment or use default
SIMKL_CLIENT_ID = os.getenv("SIMKL_CLIENT_ID")

# Get scrape mode from environment
SCRAPE_MODE = os.getenv("SCRAPE_MODE", "update")  # "full" or "update"

ANILIST_API = "https://graphql.anilist.co"
SIMKL_API = "https://api.simkl.com"
KITSU_API = "https://kitsu.io/api/edge"
JIKAN_API = "https://api.jikan.moe/v4"

# Rate Limits
RATE_LIMITS = {
    "anilist": 1.0,
    "mal": 1.0,
    "kitsu": 0.5,
    "anidb": 3.0,
    "simkl": 0.5
}

class UniversalScraper:
    def __init__(self):
        self.setup_directories()
        self.checkpoint = self.load_checkpoint()
        self.cross_ref = self.load_cross_reference()
        self.mode = SCRAPE_MODE
        self.stats = {
            "mode": self.mode,
            "start_time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "services_scraped": [],
            "total_items": 0,
            "new_items": 0,
            "updated_items": 0
        }
        self.headers = {
            "simkl": {"simkl-api-key": SIMKL_CLIENT_ID},
            "anidb": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept-Language": "en-US,en;q=0.9"
            },
            "kitsu": {
                "Accept": "application/vnd.api+json",
                "Content-Type": "application/vnd.api+json"
            }
        }
        
        print(f"\n{'='*70}")
        print(f"SCRAPE MODE: {self.mode.upper()}")
        if self.mode == "full":
            print("Will scrape ALL data from scratch (unlimited)")
        else:
            print("Will check and update existing data only")
        print(f"{'='*70}\n")

    def setup_directories(self):
        services = ["anilist", "mal", "kitsu", "anidb", "simkl", "tmdb", "imdb"]
        for service in services:
            for media_type in ["anime", "manga"]:
                (BASE_DIR / service / media_type).mkdir(parents=True, exist_ok=True)
        print(f"✓ Directories created: {BASE_DIR.absolute()}\n")

    def load_checkpoint(self):
        if CHECKPOINT_FILE.exists():
            with open(CHECKPOINT_FILE, 'r') as f:
                return json.load(f)
        return {
            "anilist": {"anime": 1, "manga": 1},
            "mal": {"anime": 1, "manga": 1},
            "kitsu": {"anime": 0, "manga": 0},
            "simkl": {"anime": 1, "movies": 1}
        }

    def load_cross_reference(self):
        """Load cross-reference database for ID mapping"""
        if MAPPING_DB.exists():
            with open(MAPPING_DB, 'r') as f:
                return json.load(f)
        return {}

    def save_checkpoint(self):
        with open(CHECKPOINT_FILE, 'w') as f:
            json.dump(self.checkpoint, f, indent=2)
        with open(MAPPING_DB, 'w', encoding='utf-8') as f:
            json.dump(self.cross_ref, f, indent=2, ensure_ascii=False)
        
        # Save stats
        self.stats["end_time"] = time.strftime("%Y-%m-%d %H:%M:%S")
        self.stats["total_items"] = len(self.cross_ref)
        with open(STATS_FILE, 'w') as f:
            json.dump(self.stats, f, indent=2)

    def save_media(self, service, media_type, media_id, full_data, initial_mappings):
        """Save media file with mappings and full data"""
        folder = BASE_DIR / service / media_type.lower()
        filepath = folder / f"{media_id}.json"
        
        # Get the most complete mappings from cross-reference
        complete_mappings = self.get_complete_mappings(service, media_id, initial_mappings)
        
        # Get full metadata from ALL services
        all_metadata = self.get_all_service_metadata(complete_mappings, media_type)
        all_metadata[service] = full_data  # Add current service data
        
        record = {
            "service": service,
            "media_id": str(media_id),
            "media_type": media_type,
            "id_mappings": complete_mappings,
            "metadata_from_all_services": all_metadata,
            "last_updated": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(record, f, indent=2, ensure_ascii=False)
    
    def get_all_service_metadata(self, mappings, media_type):
        """Load full metadata from ALL services using the mappings"""
        all_metadata = {}
        
        # Check each service folder for existing data
        for service, media_id in mappings.items():
            if not media_id or service == "tmdb" or service == "imdb":
                continue
            
            try:
                filepath = BASE_DIR / service / media_type.lower() / f"{media_id}.json"
                if filepath.exists():
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        # Get the actual metadata (could be in different keys)
                        if 'full_metadata' in data:
                            all_metadata[service] = data['full_metadata']
                        elif 'metadata_from_all_services' in data and service in data['metadata_from_all_services']:
                            all_metadata[service] = data['metadata_from_all_services'][service]
            except Exception as e:
                pass
        
        return all_metadata
    
    def get_complete_mappings(self, current_service, current_id, known_mappings):
        """Find all related IDs across all services for this media"""
        # Start with what we know
        all_mappings = known_mappings.copy()
        all_mappings[current_service] = str(current_id)
        
        # Search cross-reference for any matching IDs
        for key, ref_mappings in self.cross_ref.items():
            # If any ID matches, merge all mappings
            for service, ref_id in ref_mappings.items():
                if ref_id and all_mappings.get(service) == ref_id:
                    # Found a match! Merge everything
                    for s, v in ref_mappings.items():
                        if v and not all_mappings.get(s):
                            all_mappings[s] = v
                    break
        
        return all_mappings

    def update_cross_reference(self, mappings):
        """Update the master cross-reference database"""
        # Create a unique key from all known IDs
        key_parts = []
        for service in ["anilist", "mal", "kitsu", "anidb", "simkl", "tmdb", "imdb"]:
            if mappings.get(service):
                key_parts.append(f"{service}:{mappings[service]}")
        
        if not key_parts:
            return
        
        # Use the first available ID as the key
        primary_key = key_parts[0]
        
        # Merge with existing data if any
        if primary_key in self.cross_ref:
            existing = self.cross_ref[primary_key]
            for k, v in mappings.items():
                if v and not existing.get(k):
                    existing[k] = v
        else:
            self.cross_ref[primary_key] = mappings

    # ========================================================================
    # ANILIST SCRAPER
    # ========================================================================
    def scrape_anilist(self, media_type):
        """Scrape complete AniList database"""
        print(f"\n{'='*70}")
        print(f"SCRAPING ANILIST - {media_type.upper()}")
        print(f"{'='*70}\n")
        
        page = self.checkpoint["anilist"][media_type]
        
        while True:
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
            
            try:
                r = requests.post(ANILIST_API, json={
                    'query': query,
                    'variables': {'page': page, 'type': media_type.upper()}
                }, timeout=20)
                data = r.json().get('data', {}).get('Page', {})
            except Exception as e:
                print(f"[!] Error: {e}. Retrying...")
                time.sleep(10)
                continue
            
            if not data or not data.get('media'):
                break
            
            media_list = data['media']
            info = data['pageInfo']
            print(f"Page {info['currentPage']}/{info['lastPage']} - {len(media_list)} items")
            
            for media in media_list:
                al_id = media['id']
                
                # In UPDATE mode, skip if file exists and is recent
                if self.mode == "update":
                    check_file = BASE_DIR / "anilist" / media_type / f"{al_id}.json"
                    if check_file.exists():
                        # Check if file is less than 7 days old
                        file_age = time.time() - check_file.stat().st_mtime
                        if file_age < 7 * 24 * 3600:  # 7 days
                            continue
                        self.stats["updated_items"] += 1
                    else:
                        self.stats["new_items"] += 1
                else:
                    self.stats["new_items"] += 1
                
                # Build ID mappings from external links
                mappings = {
                    "anilist": al_id,
                    "mal": media.get('idMal', ''),
                    "kitsu": "", "anidb": "", "simkl": "", "tmdb": "", "imdb": ""
                }
                
                for link in media.get('externalLinks', []):
                    site = link['site'].lower()
                    url = link['url']
                    if "kitsu" in site:
                        mappings["kitsu"] = url.split('/')[-1]
                    elif "anidb" in site:
                        mappings["anidb"] = url.split('=')[-1]
                
                self.save_media("anilist", media_type, al_id, media, mappings)
                self.update_cross_reference(mappings)
                print(f"  ✓ AniList {al_id}: {media['title']['romaji'][:50]}")
            
            self.checkpoint["anilist"][media_type] = page
            self.save_checkpoint()
            
            if not info['hasNextPage']:
                break
            page += 1
            time.sleep(RATE_LIMITS["anilist"])
        
        print(f"\n✓✓✓ AniList {media_type} complete!\n")

    # ========================================================================
    # MAL SCRAPER (via Jikan API)
    # ========================================================================
    def scrape_mal(self, media_type):
        """Scrape complete MAL database via Jikan"""
        print(f"\n{'='*70}")
        print(f"SCRAPING MAL - {media_type.upper()}")
        print(f"{'='*70}\n")
        
        page = self.checkpoint["mal"][media_type]
        endpoint = media_type  # "anime" or "manga"
        
        while True:
            try:
                r = requests.get(f"{JIKAN_API}/{endpoint}?page={page}&limit=25", timeout=15)
                if r.status_code == 429:  # Rate limited
                    print("Rate limited. Waiting 60s...")
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
                    
                    # In UPDATE mode, skip if exists and recent
                    if self.mode == "update":
                        check_file = BASE_DIR / "mal" / media_type / f"{mal_id}.json"
                        if check_file.exists():
                            file_age = time.time() - check_file.stat().st_mtime
                            if file_age < 7 * 24 * 3600:
                                continue
                            self.stats["updated_items"] += 1
                        else:
                            self.stats["new_items"] += 1
                    else:
                        self.stats["new_items"] += 1
                    
                    # Get full details for this item
                    try:
                        detail_r = requests.get(f"{JIKAN_API}/{endpoint}/{mal_id}/full", timeout=15)
                        time.sleep(RATE_LIMITS["mal"])
                        full_data = detail_r.json().get('data', {})
                    except:
                        full_data = item
                    
                    # Build mappings
                    mappings = {
                        "mal": mal_id,
                        "anilist": "", "kitsu": "", "anidb": "", "simkl": "", "tmdb": "", "imdb": ""
                    }
                    
                    # Try to extract external IDs from MAL's external links if available
                    externals = full_data.get('external', [])
                    for ext in externals:
                        url = ext.get('url', '').lower()
                        if 'anilist' in url:
                            mappings["anilist"] = url.split('/')[-1]
                        elif 'anidb' in url:
                            match = re.search(r'aid=(\d+)', url)
                            if match:
                                mappings["anidb"] = match.group(1)
                    
                    self.save_media("mal", media_type, mal_id, full_data, mappings)
                    self.update_cross_reference(mappings)
                    print(f"  ✓ MAL {mal_id}: {full_data.get('title', 'Unknown')[:50]}")
                
                self.checkpoint["mal"][media_type] = page
                self.save_checkpoint()
                
                if not pagination.get('has_next_page'):
                    break
                page += 1
                time.sleep(RATE_LIMITS["mal"])
                
            except Exception as e:
                print(f"[!] Error: {e}. Retrying...")
                time.sleep(10)
        
        print(f"\n✓✓✓ MAL {media_type} complete!\n")

    # ========================================================================
    # KITSU SCRAPER
    # ========================================================================
    def scrape_kitsu(self, media_type):
        """Scrape complete Kitsu database"""
        print(f"\n{'='*70}")
        print(f"SCRAPING KITSU - {media_type.upper()}")
        print(f"{'='*70}\n")
        
        offset = self.checkpoint["kitsu"][media_type]
        limit = 20
        
        while True:
            try:
                r = requests.get(
                    f"{KITSU_API}/{media_type}?page[limit]={limit}&page[offset]={offset}",
                    headers=self.headers["kitsu"],
                    timeout=15
                )
                
                if r.status_code != 200:
                    print(f"Error {r.status_code}. Stopping Kitsu scrape.")
                    break
                
                data = r.json()
                items = data.get('data', [])
                
                if not items:
                    break
                
                print(f"Offset {offset} - {len(items)} items")
                
                for item in items:
                    kitsu_id = item['id']
                    attrs = item.get('attributes', {})
                    
                    # In UPDATE mode, skip if exists and recent
                    if self.mode == "update":
                        check_file = BASE_DIR / "kitsu" / media_type / f"{kitsu_id}.json"
                        if check_file.exists():
                            file_age = time.time() - check_file.stat().st_mtime
                            if file_age < 7 * 24 * 3600:
                                continue
                            self.stats["updated_items"] += 1
                        else:
                            self.stats["new_items"] += 1
                    else:
                        self.stats["new_items"] += 1
                    
                    # Build mappings - Kitsu doesn't provide external IDs directly
                    mappings = {
                        "kitsu": kitsu_id,
                        "anilist": "", "mal": "", "anidb": "", "simkl": "", "tmdb": "", "imdb": ""
                    }
                    
                    # Try to get mappings from included relationships
                    relationships = item.get('relationships', {})
                    mappings_rel = relationships.get('mappings', {})
                    
                    self.save_media("kitsu", media_type, kitsu_id, item, mappings)
                    self.update_cross_reference(mappings)
                    print(f"  ✓ Kitsu {kitsu_id}: {attrs.get('canonicalTitle', 'Unknown')[:50]}")
                
                self.checkpoint["kitsu"][media_type] = offset
                self.save_checkpoint()
                
                offset += limit
                time.sleep(RATE_LIMITS["kitsu"])
                
            except Exception as e:
                print(f"[!] Error: {e}. Retrying...")
                time.sleep(10)
        
        print(f"\n✓✓✓ Kitsu {media_type} complete!\n")

    # ========================================================================
    # SIMKL SCRAPER
    # ========================================================================
    def scrape_simkl(self, media_type):
        """Scrape Simkl database"""
        print(f"\n{'='*70}")
        print(f"SCRAPING SIMKL - {media_type.upper()}")
        print(f"{'='*70}\n")
        
        # Simkl doesn't have a direct "list all" endpoint
        # We need to use different approach - search by year or use other services' IDs
        print("Note: Simkl requires cross-referencing from other services")
        print("Enrichment will happen during cross-reference phase\n")

    # ========================================================================
    # CROSS-REFERENCE ENRICHMENT & UPDATE ALL FILES
    # ========================================================================
    def enrich_cross_references(self):
        """Fill in missing IDs by cross-referencing"""
        print(f"\n{'='*70}")
        print("ENRICHING CROSS-REFERENCES")
        print(f"{'='*70}\n")
        
        enriched = 0
        
        for key, mappings in self.cross_ref.items():
            # If we have MAL ID but no Simkl, fetch it
            if mappings.get('mal') and not mappings.get('simkl'):
                try:
                    r = requests.get(
                        f"{SIMKL_API}/search/id?mal={mappings['mal']}",
                        headers=self.headers["simkl"],
                        timeout=10
                    )
                    data = r.json()
                    if isinstance(data, list) and data:
                        simkl_id = data[0]['ids'].get('simkl')
                        if simkl_id:
                            mappings['simkl'] = simkl_id
                            enriched += 1
                            print(f"  ✓ Enriched {key} with Simkl ID: {simkl_id}")
                    time.sleep(RATE_LIMITS["simkl"])
                except:
                    pass
            
            # If we have AniDB and it's anime, scrape for TMDB/IMDB
            if mappings.get('anidb'):
                try:
                    url = f"https://anidb.net/anime/{mappings['anidb']}"
                    r = requests.get(url, headers=self.headers["anidb"], timeout=15)
                    if r.status_code == 200:
                        soup = BeautifulSoup(r.text, 'html.parser')
                        for link in soup.select('a.external'):
                            href = link.get('href', '').lower()
                            if 'themoviedb.org' in href and not mappings.get('tmdb'):
                                mappings['tmdb'] = href.rstrip('/').split('/')[-1]
                                enriched += 1
                            elif 'imdb.com/title/' in href and not mappings.get('imdb'):
                                match = re.search(r'tt\d+', href)
                                if match:
                                    mappings['imdb'] = match.group()
                                    enriched += 1
                        time.sleep(RATE_LIMITS["anidb"])
                        print(f"  ✓ Enriched {key} from AniDB")
                except:
                    pass
        
        self.save_checkpoint()
        print(f"\n✓✓✓ Enrichment complete! Added {enriched} new mappings\n")
    
    def update_all_files_with_mappings(self):
        """Update ALL media files with complete cross-referenced mappings AND metadata"""
        print(f"\n{'='*70}")
        print("UPDATING ALL FILES WITH COMPLETE MAPPINGS & METADATA")
        print(f"{'='*70}\n")
        
        updated_count = 0
        
        # First pass: collect all metadata
        print("Pass 1: Collecting all metadata...")
        all_media_data = {}
        
        for service_dir in BASE_DIR.iterdir():
            if not service_dir.is_dir():
                continue
            
            service = service_dir.name
            
            for media_type_dir in service_dir.iterdir():
                if not media_type_dir.is_dir():
                    continue
                
                media_type = media_type_dir.name
                
                for media_file in media_type_dir.glob("*.json"):
                    try:
                        with open(media_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        
                        # Create a unique key for this media
                        key = f"{service}:{data['media_id']}"
                        all_media_data[key] = {
                            'service': service,
                            'media_type': media_type,
                            'media_id': data['media_id'],
                            'mappings': data.get('id_mappings', {}),
                            'metadata': data.get('full_metadata') or data.get('metadata_from_all_services', {}).get(service, {})
                        }
                    except Exception as e:
                        pass
        
        print(f"Collected {len(all_media_data)} media entries")
        
        # Second pass: update all files with complete data
        print("\nPass 2: Updating all files...")
        
        for service_dir in BASE_DIR.iterdir():
            if not service_dir.is_dir():
                continue
            
            service = service_dir.name
            print(f"\nUpdating {service.upper()} files...")
            
            for media_type_dir in service_dir.iterdir():
                if not media_type_dir.is_dir():
                    continue
                
                media_type = media_type_dir.name
                
                for media_file in media_type_dir.glob("*.json"):
                    try:
                        # Load existing file
                        with open(media_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        
                        current_id = data['media_id']
                        current_mappings = data.get('id_mappings', {})
                        
                        # Get complete mappings from cross-reference
                        complete_mappings = self.get_complete_mappings(
                            service, 
                            current_id, 
                            current_mappings
                        )
                        
                        # Collect metadata from ALL related services
                        all_metadata = {}
                        
                        for related_service, related_id in complete_mappings.items():
                            if not related_id:
                                continue
                            
                            # Find this media in our collected data
                            search_key = f"{related_service}:{related_id}"
                            
                            if search_key in all_media_data:
                                all_metadata[related_service] = all_media_data[search_key]['metadata']
                            else:
                                # Try to load from file
                                try:
                                    related_file = BASE_DIR / related_service / media_type / f"{related_id}.json"
                                    if related_file.exists():
                                        with open(related_file, 'r', encoding='utf-8') as f:
                                            related_data = json.load(f)
                                            if 'full_metadata' in related_data:
                                                all_metadata[related_service] = related_data['full_metadata']
                                            elif 'metadata_from_all_services' in related_data:
                                                if related_service in related_data['metadata_from_all_services']:
                                                    all_metadata[related_service] = related_data['metadata_from_all_services'][related_service]
                                except:
                                    pass
                        
                        # Update the file
                        data['id_mappings'] = complete_mappings
                        data['metadata_from_all_services'] = all_metadata
                        data['last_updated'] = time.strftime("%Y-%m-%d %H:%M:%S")
                        
                        # Remove old 'full_metadata' key if it exists
                        if 'full_metadata' in data:
                            # Move it to the new structure
                            if service not in all_metadata:
                                all_metadata[service] = data['full_metadata']
                                data['metadata_from_all_services'] = all_metadata
                            del data['full_metadata']
                        
                        with open(media_file, 'w', encoding='utf-8') as f:
                            json.dump(data, f, indent=2, ensure_ascii=False)
                        
                        updated_count += 1
                        
                        if updated_count % 50 == 0:
                            print(f"  Updated {updated_count} files...")
                    
                    except Exception as e:
                        print(f"  [!] Error updating {media_file}: {e}")
        
        print(f"\n✓✓✓ Updated {updated_count} files with complete metadata from ALL services!\n")

    # ========================================================================
    # MAIN EXECUTION
    # ========================================================================
    def run(self):
        print("\n" + "="*70)
        print("UNIVERSAL ANIME/MANGA SCRAPER")
        print("Scraping ALL services independently")
        print("="*70 + "\n")
        
        if self.mode == "full":
            # FULL MODE: Scrape everything unlimited
            print("🔄 FULL SCRAPE MODE - Getting ALL data from ALL services\n")
            services_to_scrape = [
                ("anilist", ["anime", "manga"]),
                ("mal", ["anime", "manga"]),
                ("kitsu", ["anime", "manga"]),
                ("simkl", ["anime"])
            ]
            
            for service, types in services_to_scrape:
                self.stats["services_scraped"].append(service)
                for media_type in types:
                    scraper_method = getattr(self, f"scrape_{service}")
                    scraper_method(media_type)
        else:
            # UPDATE MODE: Only check for new/updated entries
            print("🔄 UPDATE MODE - Checking for new/updated entries\n")
            print("Will update entries older than 7 days\n")
            
            # Run update scrape with limited pages
            services_to_scrape = [
                ("anilist", ["anime", "manga"]),
                ("mal", ["anime", "manga"]),
                ("kitsu", ["anime", "manga"]),
                ("simkl", ["anime"])
            ]
            
            for service, types in services_to_scrape:
                self.stats["services_scraped"].append(service)
                for media_type in types:
                    scraper_method = getattr(self, f"scrape_{service}")
                    scraper_method(media_type)
        
        # Enrich cross-references
        self.enrich_cross_references()
        
        # Update ALL files with complete mappings
        self.update_all_files_with_mappings()
        
        # Save final stats
        self.save_checkpoint()
        
        print("\n" + "="*70)
        print("SCRAPING COMPLETE!")
        print(f"Mode: {self.mode.upper()}")
        print(f"Database location: {BASE_DIR.absolute()}")
        print(f"Cross-reference: {MAPPING_DB.absolute()}")
        print(f"Total unique media: {len(self.cross_ref)}")
        print(f"New items: {self.stats['new_items']}")
        print(f"Updated items: {self.stats['updated_items']}")
        print("\nEach media file now contains:")
        print("  - ID mappings to ALL services")
        print("  - Full metadata from AniList")
        print("  - Full metadata from MAL")
        print("  - Full metadata from Kitsu")
        print("  - Full metadata from AniDB")
        print("  - Full metadata from Simkl")
        print("  - Full metadata from TMDB (if available)")
        print("  - Full metadata from IMDB (if available)")
        print("\n  ALL DATA IN EVERY FILE!")
        print("="*70 + "\n")

if __name__ == "__main__":
    scraper = UniversalScraper()
    scraper.run()
