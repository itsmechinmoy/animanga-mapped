"""
Merge and Enrich Script
Combines all parallel scrape results and builds cross-references
Updates every file with data from ALL services in flat structure
Supports: AniList, MAL, Kitsu, SIMKL, TMDB, IMDB, AniDB
"""

import json
import time
from pathlib import Path
from collections import defaultdict

BASE_DIR = Path("media_database")
ARTIFACTS_DIR = Path("artifacts")
CROSS_REF_FILE = Path("cross_reference.json")

class MergeEnricher:
    """Merges parallel scrape results and enriches with cross-service data"""
    
    def __init__(self):
        self.cross_ref = {}
        self.all_media = {}  # {media_key: media_info}
        
        print(f"\n{'='*70}")
        print("MERGING ALL PARALLEL SCRAPE RESULTS")
        print("Services: AniList, MAL, Kitsu, SIMKL")
        print(f"{'='*70}\n")
    
    def merge_artifacts(self):
        """Merge all downloaded artifacts into organized structure"""
        print("Step 1: Merging artifacts from parallel jobs...")
        
        # Create base structure
        BASE_DIR.mkdir(exist_ok=True)
        
        # Process each artifact directory
        for artifact_dir in ARTIFACTS_DIR.iterdir():
            if not artifact_dir.is_dir() or not artifact_dir.name.startswith('data-'):
                continue
            
            service_type = artifact_dir.name.replace('data-', '')
            print(f"  Processing {service_type}...")
            
            # Find the actual data directory (artifacts are nested)
            source_dir = artifact_dir / "media_database" / service_type
            if not source_dir.exists():
                # Try without nesting
                source_dir = artifact_dir
            
            if not source_dir.exists():
                print(f"    [WARN] Source directory not found for {service_type}")
                continue
            
            # Copy to final location
            dest_dir = BASE_DIR / service_type
            dest_dir.mkdir(parents=True, exist_ok=True)
            
            count = 0
            for json_file in source_dir.glob("*.json"):
                # Skip stats files
                if json_file.name == "stats.json":
                    continue
                
                try:
                    # Read the data
                    with open(json_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # Store in memory for cross-referencing
                    service, media_type = service_type.split('-')
                    media_key = f"{service}:{data['media_id']}"
                    
                    self.all_media[media_key] = {
                        'service': service,
                        'media_type': media_type,
                        'media_id': data['media_id'],
                        'mappings': data.get('id_mappings', {}),
                        'data': data.get('data', {})
                    }
                    
                    count += 1
                except Exception as e:
                    print(f"    [ERROR] Failed to read {json_file}: {e}")
            
            print(f"    ✓ Merged {count} items from {service_type}")
        
        print(f"\n  Total media items collected: {len(self.all_media)}\n")
    
    def build_cross_references(self):
        """Build complete cross-reference mapping by linking all IDs"""
        print("Step 2: Building cross-references...")
        print("  (Linking AniList ↔ MAL ↔ Kitsu ↔ SIMKL ↔ TMDB/IMDB)\n")
        
        # Group media by shared IDs
        id_to_media = defaultdict(set)  # {service:id -> set of media_keys}
        
        # First pass: map each ID to all media that mention it
        for media_key, media_info in self.all_media.items():
            mappings = media_info['mappings']
            
            # For each non-empty ID this media knows about
            for service, service_id in mappings.items():
                if service_id:
                    id_key = f"{service}:{service_id}"
                    id_to_media[id_key].add(media_key)
        
        print(f"  Found {len(id_to_media)} unique service IDs")
        
        # Second pass: merge groups that share any IDs
        merged_groups = []
        processed_media = set()
        
        for media_key in self.all_media.keys():
            if media_key in processed_media:
                continue
            
            # Start a new group with this media
            current_group = {media_key}
            to_process = {media_key}
            
            # Keep expanding group until no new connections found
            while to_process:
                processing = to_process.pop()
                processed_media.add(processing)
                
                if processing not in self.all_media:
                    continue
                
                # Get all IDs this media knows about
                mappings = self.all_media[processing]['mappings']
                
                for service, service_id in mappings.items():
                    if not service_id:
                        continue
                    
                    id_key = f"{service}:{service_id}"
                    
                    # Find all media that share this ID
                    if id_key in id_to_media:
                        for related_media in id_to_media[id_key]:
                            if related_media not in current_group:
                                current_group.add(related_media)
                                if related_media not in processed_media:
                                    to_process.add(related_media)
            
            if current_group:
                merged_groups.append(current_group)
        
        print(f"  Merged into {len(merged_groups)} unique media groups")
        
        # Third pass: create combined mappings for each group
        for group in merged_groups:
            # Collect all IDs from this group
            combined_mappings = {
                "anilist": "",
                "mal": "",
                "kitsu": "",
                "anidb": "",
                "simkl": "",
                "tmdb": "",
                "imdb": ""
            }
            
            # Merge all mappings from all media in this group
            for media_key in group:
                if media_key not in self.all_media:
                    continue
                
                mappings = self.all_media[media_key]['mappings']
                for service, service_id in mappings.items():
                    if service_id and not combined_mappings.get(service):
                        combined_mappings[service] = str(service_id)
            
            # Use first available ID as the primary key
            primary_key = None
            for service in ["anilist", "mal", "kitsu", "simkl", "anidb"]:
                if combined_mappings.get(service):
                    primary_key = f"{service}:{combined_mappings[service]}"
                    break
            
            if primary_key:
                self.cross_ref[primary_key] = combined_mappings
        
        print(f"  ✓ Created {len(self.cross_ref)} cross-reference entries\n")
    
    def update_all_files(self):
        """Update EVERY file with ALL service data in FLAT structure"""
        print("Step 3: Updating all files with complete data...")
        print("  (Creating flat structure with data from ALL services)\n")
        
        updated = 0
        
        # Process each service directory
        for service_dir in BASE_DIR.iterdir():
            if not service_dir.is_dir():
                continue
            
            service_type = service_dir.name
            
            # Skip if not a valid service directory
            if '-' not in service_type:
                continue
            
            service, media_type = service_type.split('-')
            
            print(f"  Updating {service_type}...")
            
            for json_file in service_dir.glob("*.json"):
                if json_file.name == "stats.json":
                    continue
                
                try:
                    # Load existing file
                    with open(json_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    current_id = data['media_id']
                    current_mappings = data.get('id_mappings', {})
                    
                    # Find complete mappings from cross-reference
                    complete_mappings = None
                    for key, mappings in self.cross_ref.items():
                        if mappings.get(service) == str(current_id):
                            complete_mappings = mappings
                            break
                    
                    # Fallback to current mappings if not found in cross-ref
                    if not complete_mappings:
                        complete_mappings = current_mappings
                    
                    # Build FLAT structure with data from ALL services
                    updated_record = {
                        "service": service,
                        "media_id": str(current_id),
                        "media_type": media_type,
                        "last_updated": time.strftime("%Y-%m-%d %H:%M:%S")
                    }
                    
                    # Add data from EACH service as top-level keys
                    for other_service in ["anilist", "mal", "kitsu", "anidb", "simkl", "tmdb", "imdb"]:
                        other_id = complete_mappings.get(other_service)
                        
                        if not other_id:
                            updated_record[other_service] = None
                            continue
                        
                        # Find this service's data
                        search_key = f"{other_service}:{other_id}"
                        
                        if search_key in self.all_media:
                            # Add the complete data from this service
                            updated_record[other_service] = self.all_media[search_key]['data']
                        else:
                            # Try to load from file system
                            found = False
                            for other_dir in BASE_DIR.iterdir():
                                if not other_dir.is_dir():
                                    continue
                                if not other_dir.name.startswith(f"{other_service}-"):
                                    continue
                                
                                other_file = other_dir / f"{other_id}.json"
                                if other_file.exists():
                                    try:
                                        with open(other_file, 'r', encoding='utf-8') as f:
                                            other_data = json.load(f)
                                            updated_record[other_service] = other_data.get('data', {})
                                            found = True
                                            break
                                    except:
                                        pass
                            
                            if not found:
                                updated_record[other_service] = None
                    
                    # Write the updated file with FLAT structure
                    with open(json_file, 'w', encoding='utf-8') as f:
                        json.dump(updated_record, f, indent=2, ensure_ascii=False)
                    
                    updated += 1
                    
                    if updated % 100 == 0:
                        print(f"    Updated {updated} files...")
                
                except Exception as e:
                    print(f"    [ERROR] Failed to update {json_file}: {e}")
        
        print(f"\n  ✓ Updated {updated} files with complete data from all services\n")
    
    def save_cross_reference(self):
        """Save final cross-reference database"""
        print("Step 4: Saving cross-reference database...")
        
        with open(CROSS_REF_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.cross_ref, f, indent=2, ensure_ascii=False)
        
        print(f"  ✓ Saved to {CROSS_REF_FILE.absolute()}\n")
    
    def generate_summary(self):
        """Generate final summary"""
        # Count items by service
        service_counts = defaultdict(int)
        for media_info in self.all_media.values():
            service_counts[media_info['service']] += 1
        
        print(f"{'='*70}")
        print("MERGE AND ENRICH COMPLETE!")
        print(f"{'='*70}")
        print(f"Total unique media: {len(self.cross_ref)}")
        print(f"Database location: {BASE_DIR.absolute()}")
        print(f"Cross-reference: {CROSS_REF_FILE.absolute()}")
        print(f"\nItems by Service:")
        for service, count in sorted(service_counts.items()):
            print(f"  {service}: {count}")
        print(f"\nFile Structure (FLAT):")
        print("  {")
        print('    "service": "anilist",')
        print('    "media_id": "12345",')
        print('    "media_type": "anime",')
        print('    "last_updated": "2026-01-20 14:30:00",')
        print('    ')
        print('    "anilist": { /* complete AniList data */ },')
        print('    "mal": { /* complete MAL data */ },')
        print('    "kitsu": { /* complete Kitsu data */ },')
        print('    "simkl": { /* complete SIMKL data */ },')
        print('    "anidb": null,  // if not available')
        print('    "tmdb": null,')
        print('    "imdb": null')
        print("  }")
        print(f"{'='*70}\n")
    
    def run(self):
        """Execute the complete merge and enrich process"""
        self.merge_artifacts()
        self.build_cross_references()
        self.update_all_files()
        self.save_cross_reference()
        self.generate_summary()

if __name__ == "__main__":
    merger = MergeEnricher()
    merger.run()
