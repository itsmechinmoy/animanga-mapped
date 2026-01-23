"""
Manga mapper - merges manga data using AniList as base ID
Only uses: AniList, MyAnimeList, Kitsu
File: mappers/manga_mapper.py
"""
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import defaultdict
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.file_utils import load_json, save_json

class MangaMapper:
    """Maps and merges manga data from all services"""
    
    # Only these services for manga
    SERVICES = ['anilist', 'myanimelist', 'kitsu']
    
    # Field name mapping
    FIELD_MAP = {
        'anilist': 'anilist_id',
        'mal': 'mal_id',
        'myanimelist': 'mal_id',
        'kitsu': 'kitsu_id'
    }
    
    def __init__(self):
        self.scraped_dir = Path("scraped-data/manga")
        self.output_file = Path("mapped-data/manga-list-full-mapped.json")
        self.output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Storage
        self.id_graph = defaultdict(lambda: defaultdict(set))
        self.all_data = {}
        
        print(f"\n{'='*70}")
        print("MANGA MAPPER - Merging all service data")
        print(f"Base ID: AniList")
        print(f"Services: AniList, MyAnimeList, Kitsu")
        print(f"{'='*70}\n")
    
    def load_all_data(self):
        """Load data from all service files"""
        print("Step 1: Loading data from all services...")
        
        for service in self.SERVICES:
            filepath = self.scraped_dir / f"{service}-manga.json"
            
            if not filepath.exists():
                print(f"  [SKIP] {service}: file not found")
                continue
            
            try:
                data = load_json(filepath)
                print(f"  ✓ {service}: {len(data)} items")
                
                for item in data:
                    item_id = item.get('id')
                    if not item_id:
                        continue
                    
                    # Store full data
                    self.all_data[(service, item_id)] = item
                    
                    # Build ID graph
                    external_ids = item.get('external_ids', {})
                    all_ids = {service: item_id, **external_ids}
                    
                    # Link all IDs together
                    for svc, svc_id in all_ids.items():
                        if svc_id:
                            self.id_graph[svc][str(svc_id)].update(
                                (s, str(i)) for s, i in all_ids.items() if i
                            )
            
            except Exception as e:
                print(f"  [ERROR] {service}: {e}")
        
        print(f"\nTotal items loaded: {len(self.all_data)}\n")
    
    def build_cross_references(self) -> Dict[str, Dict[str, str]]:
        """Build complete cross-reference map"""
        print("Step 2: Building cross-references...")
        
        visited = set()
        clusters = []
        
        for service, id_map in self.id_graph.items():
            for item_id in id_map.keys():
                key = (service, item_id)
                
                if key in visited:
                    continue
                
                # BFS to find all connected IDs
                cluster = set()
                queue = [key]
                
                while queue:
                    curr_service, curr_id = queue.pop(0)
                    curr_key = (curr_service, curr_id)
                    
                    if curr_key in visited:
                        continue
                    
                    visited.add(curr_key)
                    cluster.add(curr_key)
                    
                    for related_service, related_id in self.id_graph[curr_service].get(curr_id, set()):
                        related_key = (related_service, related_id)
                        if related_key not in visited:
                            queue.append(related_key)
                
                if cluster:
                    clusters.append(cluster)
        
        print(f"  Found {len(clusters)} unique manga clusters\n")
        
        # Convert clusters to ID mappings
        cross_ref = {}
        
        for cluster in clusters:
            ids = {}
            for service, item_id in cluster:
                normalized = self.normalize_service_name(service)
                if normalized not in ids:
                    ids[normalized] = str(item_id)
            
            # Use AniList as primary key (required for manga)
            if 'anilist' in ids:
                primary_key = f"anilist:{ids['anilist']}"
                cross_ref[primary_key] = ids
            else:
                # If no AniList ID, use MAL or Kitsu
                for svc in ['mal', 'myanimelist', 'kitsu']:
                    normalized = self.normalize_service_name(svc)
                    if normalized in ids:
                        primary_key = f"{normalized}:{ids[normalized]}"
                        cross_ref[primary_key] = ids
                        break
        
        return cross_ref
    
    def merge_to_final_format(self, cross_ref: Dict[str, Dict[str, str]]) -> List[Dict[str, Any]]:
        """Merge all data into final format"""
        print("Step 3: Merging into final format...")
        
        final_list = []
        
        for primary_key, id_map in cross_ref.items():
            try:
                item = {}
                
                # Add type
                item_type = self.get_type_from_sources(id_map)
                if item_type:
                    item['type'] = item_type
                
                # Add all IDs
                for service, service_id in id_map.items():
                    field_name = self.FIELD_MAP.get(service)
                    if field_name:
                        try:
                            # STRICTLY enforce integers for IDs
                            item[field_name] = int(service_id)
                        except (ValueError, TypeError):
                            # If conversion fails, ignore this ID entirely
                            # This prevents strings from entering the final data and breaking the sort
                            # print(f"  [WARN] Ignored invalid non-numeric ID for {service}: {service_id}")
                            pass
                
                # Only add item if it has at least one valid ID
                if any(k in item for k in self.FIELD_MAP.values()):
                    final_list.append(item)
            
            except Exception as e:
                print(f"  [WARN] Failed to merge {primary_key}: {e}")
        
        # Sort by AniList ID
        # Now safe because anilist_id is guaranteed to be int or None
        final_list.sort(key=lambda x: (
            x.get('anilist_id') is None,
            x.get('anilist_id', 999999999)
        ))
        
        print(f"  Created {len(final_list)} final entries\n")
        
        return final_list
    
    def get_type_from_sources(self, id_map: Dict[str, str]) -> Optional[str]:
        """Get manga type from available sources"""
        for service in ['anilist', 'mal', 'myanimelist', 'kitsu']:
            normalized = self.normalize_service_name(service)
            if normalized in id_map:
                key = (service, id_map[normalized])
                if key in self.all_data:
                    item_type = self.all_data[key].get('type')
                    if item_type:
                        return item_type
        return None
    
    def normalize_service_name(self, service: str) -> str:
        """Normalize service names"""
        if service.lower() == 'myanimelist':
            return 'mal'
        return service.lower()
    
    def run(self):
        """Execute the mapping process"""
        self.load_all_data()
        cross_ref = self.build_cross_references()
        final_data = self.merge_to_final_format(cross_ref)
        
        # Save output
        save_json(self.output_file, final_data, pretty=True)
        
        print(f"{'='*70}")
        print("MANGA MAPPING COMPLETE!")
        print(f"Output: {self.output_file}")
        print(f"Total entries: {len(final_data)}")
        print(f"{'='*70}\n")
