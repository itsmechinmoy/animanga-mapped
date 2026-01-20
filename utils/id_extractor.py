"""
ID extraction utilities
"""
import re
from typing import Optional
from urllib.parse import urlparse

def extract_id_from_url(url: str, service: str) -> Optional[str]:
    """Extract ID from service URL"""
    
    if not url:
        return None
    
    service = service.lower()
    
    # AniDB
    if service == 'anidb':
        match = re.search(r'aid=(\d+)', url) or re.search(r'/anime/(\d+)', url)
        return match.group(1) if match else None
    
    # AniList
    elif service == 'anilist':
        match = re.search(r'/anime/(\d+)', url) or re.search(r'/manga/(\d+)', url)
        return match.group(1) if match else None
    
    # MyAnimeList
    elif service in ['mal', 'myanimelist']:
        match = re.search(r'/anime/(\d+)', url) or re.search(r'/manga/(\d+)', url)
        return match.group(1) if match else None
    
    # Kitsu
    elif service == 'kitsu':
        match = re.search(r'/anime/(\d+)', url) or re.search(r'/manga/(\d+)', url)
        if match:
            return match.group(1)
        # Sometimes kitsu uses slug
        match = re.search(r'/anime/([^/]+)', url) or re.search(r'/manga/([^/]+)', url)
        return match.group(1) if match else None
    
    # SIMKL
    elif service == 'simkl':
        match = re.search(r'/anime/(\d+)', url) or re.search(r'/movies/(\d+)', url)
        return match.group(1) if match else None
    
    # TMDB
    elif service in ['themoviedb', 'tmdb']:
        match = re.search(r'/tv/(\d+)', url) or re.search(r'/movie/(\d+)', url)
        return match.group(1) if match else None
    
    # TVDB
    elif service in ['thetvdb', 'tvdb']:
        match = re.search(r'/series/(\d+)', url) or re.search(r'id=(\d+)', url)
        return match.group(1) if match else None
    
    # IMDB
    elif service == 'imdb':
        match = re.search(r'(tt\d+)', url)
        return match.group(1) if match else None
    
    # Anime-Planet
    elif service in ['animeplanet', 'anime-planet']:
        # anime-planet uses slugs
        parsed = urlparse(url)
        path_parts = parsed.path.strip('/').split('/')
        if len(path_parts) >= 2:
            return path_parts[-1]
        return None
    
    # AnimeNewsNetwork
    elif service in ['animenewsnetwork', 'ann']:
        match = re.search(r'id=(\d+)', url)
        return match.group(1) if match else None
    
    # Livechart
    elif service == 'livechart':
        match = re.search(r'/anime/(\d+)', url)
        return match.group(1) if match else None
    
    return None
