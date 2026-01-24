"""
Anime mapper - merges all service data using AniDB as base ID
File: mappers/anime_mapper.py
"""
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import defaultdict
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.file_utils import load_json, save_json

class AnimeMapper:
    """Maps and merges anime data from all services"""
    
    # Services to process
    SERVICES = [
        'anidb', 'anilist', 'myanimelist', 'animenewsnetwork',
        'animeplanet', 'kitsu', 'livechart', 'simkl',
        'themoviedb', 'tvdb', 'imdb'
    ]
    
    # Field name mapping to final format
    FIELD_MAP = {
        'anidb': 'anidb_id',
        'anilist': 'anilist_id',
        'mal': 'mal_id',
        'myanimelist': 'mal_id',
        'animenewsnetwork': 'animenewsnetwork_id',
        'animeplanet': 'anime-planet_id',
        'anime-planet': 'anime-planet_id',
        'kitsu': 'kitsu_id',
        'livechart': 'livechart_id',
        'simkl': 'simkl_id',
        'themoviedb': 'themoviedb_id',
        'tmdb': 'themoviedb_id',
        'tvdb': 'tvdb_id',
        'thetvdb': 'tvdb_id',
        'imdb': 'imdb_id'
    }
    
    def __init__(self):
        self.scraped_dir = Path("scraped-data/anime")
        self.output_file = Path("mapped-data/anime-list-full-mapped.json")
        self.output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Storage
        self.id_graph = defaultdict(lambda: defaultdict(set))  # service -> id -> set of all related IDs
        self.all_data = {}  # (service, id) -> full item data
        
        print(f"\n{'='*70}")
        print("ANIME MAPPER - Merging all service data")
        print(f"Base ID: AniDB")
        print(f"{'='*70}\n")
    
    def load_all_data(self):
        """Load data from all service files"""
        print("Step 1: Loading data from all services...")
        
        for service in self.SERVICES:
            filepath = self.scraped_dir / f"{service}-anime.json"
            
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
        """Build complete cross-reference map by connecting related IDs"""
        print("Step 2: Building cross-references...")
        
        # Find all connected ID clusters using BFS
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
                    
                    # Get all related IDs
                    for related_service, related_id in self.id_graph[curr_service].get(curr_id, set()):
                        related_key = (related_service, related_id)
                        if related_key not in visited:
                            queue.append(related_key)
                
                if cluster:
                    clusters.append(cluster)
        
        print(f"  Found {len(clusters)} unique anime clusters\n")
        
        # Convert clusters to ID mappings
        cross_ref = {}
        
        for cluster in clusters:
            # Collect all IDs from this cluster
            ids = {}
            for service, item_id in cluster:
                normalized = self.normalize_service_name(service)
                if normalized not in ids:
                    ids[normalized] = str(item_id)
            
            # Use AniDB as primary key if available, otherwise first available
            primary_key = None
            if 'anidb' in ids:
                primary_key = f"anidb:{ids['anidb']}"
            else:
                # Fallback to first available ID
                for svc in ['anilist', 'mal', 'kitsu', 'simkl']:
                    if svc in ids:
                        primary_key = f"{svc}:{ids[svc]}"
                        break
            
            if primary_key:
                cross_ref[primary_key] = ids
        
        return cross_ref
    
    def merge_to_final_format(self, cross_ref: Dict[str, Dict[str, str]]) -> List[Dict[str, Any]]:
        """Merge all data into final format"""
        print("Step 3: Merging into final format...")
        
        final_list = []
        
        for primary_key, id_map in cross_ref.items():
            try:
                # Build the final item
                item = {}
                
                # Add type (get from any available source)
                item_type = self.get_type_from_sources(id_map)
                if item_type:
                    item['type'] = item_type
                
                # Add all IDs in the correct format
                for service, service_id in id_map.items():
                    field_name = self.FIELD_MAP.get(service)
                    if field_name:
                        # Special handling for anime-planet (keep as string)
                        if service == 'animeplanet' or service == 'anime-planet':
                            item[field_name] = str(service_id)
                        else:
                            # STRICTLY enforce integers for all other IDs (AniDB, MAL, etc.)
                            try:
                                item[field_name] = int(service_id)
                            except (ValueError, TypeError):
                                # If conversion fails, IGNORE the ID. 
                                # Do NOT fallback to string, or sorting will crash.
                                pass
                
                # Add season info if available
                season = self.extract_season_info(id_map)
                if season:
                    item['season'] = season
                
                # Only add item if it has at least one valid ID (optional but good practice)
                if any(k in item for k in self.FIELD_MAP.values()):
                    final_list.append(item)
            
            except Exception as e:
                print(f"  [WARN] Failed to merge {primary_key}: {e}")
        
        # Sort by AniDB ID if available
        # Safe now because anidb_id is guaranteed to be int or None
        final_list.sort(key=lambda x: (
            x.get('anidb_id') is None,
            x.get('anidb_id', 999999999)
        ))
        
        print(f"  Created {len(final_list)} final entries\n")
        
        return final_list
    
    def get_type_from_sources(self, id_map: Dict[str, str]) -> Optional[str]:
        """Get anime type from available sources"""
        # Priority: AniList > MAL > others
        for service in ['anilist', 'mal', 'myanimelist', 'kitsu']:
            if service in id_map:
                key = (service, id_map[service])
                if key in self.all_data:
                    item_type = self.all_data[key].get('type')
                    if item_type:
                        return item_type
        return None
    
    def extract_season_info(self, id_map: Dict[str, str]) -> Optional[Dict[str, int]]:
        """Extract season information from AniDB source"""
        season = {}
        
        # Get season info from AniDB data
        if 'anidb' in id_map:
            key = ('anidb', id_map['anidb'])
            if key in self.all_data:
                metadata = self.all_data[key].get('metadata', {})
                
                # TVDB season
                tvdb_season = metadata.get('default_tvdb_season')
                if tvdb_season and tvdb_season not in ['a', '0', 'movie', 'ova', '']:
                    try:
                        season['tvdb'] = int(tvdb_season)
                    except (ValueError, TypeError):
                        pass
                
                # TMDB season
                tmdb_season = metadata.get('tmdb_season')
                if tmdb_season and tmdb_season not in ['a', '0', '']:
                    try:
                        season['tmdb'] = int(tmdb_season)
                    except (ValueError, TypeError):
                        pass
        
        return season if season else None
    
    def normalize_service_name(self, service: str) -> str:
        """Normalize service names"""
        mapping = {
            'themoviedb': 'themoviedb',
            'thetvdb': 'tvdb',
            'anime-planet': 'animeplanet',
            'myanimelist': 'mal'
        }
        return mapping.get(service.lower(), service.lower())
    
    def run(self):
        """Execute the mapping process"""
        self.load_all_data()
        cross_ref = self.build_cross_references()
        final_data = self.merge_to_final_format(cross_ref)
        
        # Save output
        save_json(self.output_file, final_data, pretty=True)
        
        print(f"{'='*70}")
        print("ANIME MAPPING COMPLETE!")
        print(f"Output: {self.output_file}")
        print(f"Total entries: {len(final_data)}")
        print(f"{'='*70}\n")
