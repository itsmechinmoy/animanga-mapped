"""
ID extraction utilities from URLs
File: utils/id_extractor.py
"""
import re
from typing import Optional
from urllib.parse import urlparse, parse_qs

def extract_id_from_url(url: str, service: str) -> Optional[str]:
    """
    Extract ID from service URL
    
    Args:
        url: URL to parse
        service: Service name
        
    Returns:
        Extracted ID or None if not found
    """
    
    if not url:
        return None
    
    service = service.lower()
    
    try:
        # AniDB
        if service == 'anidb':
            # Format: https://anidb.net/anime/1 or ?aid=1
            match = re.search(r'aid=(\d+)', url)
            if match:
                return match.group(1)
            match = re.search(r'/anime/(\d+)', url)
            if match:
                return match.group(1)
        
        # AniList
        elif service == 'anilist':
            # Format: https://anilist.co/anime/290 or https://anilist.co/manga/30013
            match = re.search(r'/(?:anime|manga)/(\d+)', url)
            if match:
                return match.group(1)
        
        # MyAnimeList
        elif service in ['mal', 'myanimelist']:
            # Format: https://myanimelist.net/anime/290 or https://myanimelist.net/manga/2
            match = re.search(r'/(?:anime|manga)/(\d+)', url)
            if match:
                return match.group(1)
        
        # Kitsu
        elif service == 'kitsu':
            # Format: https://kitsu.io/anime/265 or https://kitsu.io/anime/crest-of-the-stars
            match = re.search(r'/(?:anime|manga)/([^/?]+)', url)
            if match:
                return match.group(1)
        
        # SIMKL
        elif service == 'simkl':
            # Format: https://simkl.com/anime/36462 or https://simkl.com/movies/...
            match = re.search(r'/(?:anime|movies|tv)/(\d+)', url)
            if match:
                return match.group(1)
        
        # TMDB (The Movie Database)
        elif service in ['themoviedb', 'tmdb']:
            # Format: https://www.themoviedb.org/tv/26209 or /movie/128
            match = re.search(r'/(?:tv|movie)/(\d+)', url)
            if match:
                return match.group(1)
        
        # TVDB (The TV Database)
        elif service in ['thetvdb', 'tvdb']:
            # Format: https://thetvdb.com/series/crest-of-the-stars or ?id=72025
            match = re.search(r'[?&]id=(\d+)', url)
            if match:
                return match.group(1)
            match = re.search(r'/series/([^/?]+)', url)
            if match:
                # Could be slug or ID
                series_id = match.group(1)
                if series_id.isdigit():
                    return series_id
                # For slug, we'd need to look it up, return slug for now
                return series_id
        
        # IMDB
        elif service == 'imdb':
            # Format: https://www.imdb.com/title/tt0286390/
            match = re.search(r'(tt\d+)', url)
            if match:
                return match.group(1)
        
        # Anime-Planet
        elif service in ['animeplanet', 'anime-planet']:
            # Format: https://www.anime-planet.com/anime/crest-of-the-stars
            parsed = urlparse(url)
            path_parts = [p for p in parsed.path.strip('/').split('/') if p]
            if len(path_parts) >= 2:
                # Return the slug (last part of path)
                return path_parts[-1]
        
        # AnimeNewsNetwork
        elif service in ['animenewsnetwork', 'ann']:
            # Format: https://www.animenewsnetwork.com/encyclopedia/anime.php?id=14
            match = re.search(r'[?&]id=(\d+)', url)
            if match:
                return match.group(1)
        
        # Livechart
        elif service == 'livechart':
            # Format: https://www.livechart.me/anime/4157
            match = re.search(r'/anime/(\d+)', url)
            if match:
                return match.group(1)
        
        # Anisearch
        elif service == 'anisearch':
            # Format: https://www.anisearch.com/anime/3039
            match = re.search(r'/anime/(\d+)', url)
            if match:
                return match.group(1)
        
        return None
        
    except Exception as e:
        print(f"  [WARN] Failed to extract ID from {url}: {e}")
        return None

def normalize_id(id_value: any) -> Optional[str]:
    """
    Normalize ID to string format
    
    Args:
        id_value: ID in any format
        
    Returns:
        Normalized string ID or None
    """
    if id_value is None:
        return None
    
    if isinstance(id_value, (int, float)):
        return str(int(id_value))
    
    if isinstance(id_value, str):
        return id_value.strip()
    
    return str(id_value)

def is_valid_id(id_value: any, service: str) -> bool:
    """
    Check if ID is valid for given service
    
    Args:
        id_value: ID to validate
        service: Service name
        
    Returns:
        True if valid, False otherwise
    """
    if not id_value:
        return False
    
    id_str = str(id_value).strip()
    
    if not id_str:
        return False
    
    service = service.lower()
    
    # Integer IDs
    if service in ['anidb', 'anilist', 'mal', 'myanimelist', 'kitsu', 
                   'simkl', 'themoviedb', 'tmdb', 'tvdb', 'thetvdb',
                   'animenewsnetwork', 'ann', 'livechart', 'anisearch']:
        return id_str.isdigit()
    
    # String IDs
    elif service in ['imdb']:
        return bool(re.match(r'tt\d+', id_str))
    
    elif service in ['animeplanet', 'anime-planet']:
        # Slugs are typically lowercase with hyphens
        return bool(re.match(r'^[a-z0-9-]+$', id_str))
    
    return True  # Default to valid for unknown services
