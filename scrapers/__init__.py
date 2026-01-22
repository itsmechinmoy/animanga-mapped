"""
Scrapers package - Contains all anime and manga scrapers
File: scrapers/__init__.py
"""

from .base_scraper import BaseScraper

# Anime scrapers
from .anime.anidb_scraper import AniDBScraper
from .anime.anilist_scraper import AniListAnimeScraper
from .anime.myanimelist_scraper import MyAnimeListAnimeScraper
from .anime.kitsu_scraper import KitsuAnimeScraper
from .anime.simkl_scraper import SIMKLAnimeScraper
from .anime.animenewsnetwork_scraper import AnimeNewsNetworkScraper
from .anime.animeplanet_scraper import AnimePlanetScraper
from .anime.livechart_scraper import LivechartScraper
from .anime.themoviedb_scraper import TMDBAnimeScraper
from .anime.tvdb_scraper import TVDBScraper
from .anime.imdb_scraper import IMDBScraper

# Manga scrapers
from .manga.anilist_scraper import AniListMangaScraper
from .manga.myanimelist_scraper import MyAnimeListMangaScraper
from .manga.kitsu_scraper import KitsuMangaScraper

__all__ = [
    'BaseScraper',
    # Anime
    'AniDBScraper',
    'AniListAnimeScraper',
    'MyAnimeListAnimeScraper',
    'KitsuAnimeScraper',
    'SIMKLAnimeScraper',
    'AnimeNewsNetworkScraper',
    'AnimePlanetScraper',
    'LivechartScraper',
    'TMDBAnimeScraper',
    'TVDBScraper',
    'IMDBScraper',
    # Manga
    'AniListMangaScraper',
    'MyAnimeListMangaScraper',
    'KitsuMangaScraper'
]
