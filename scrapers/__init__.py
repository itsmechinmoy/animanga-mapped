# scrapers/__init__.py
"""
Scrapers package
File: scrapers/__init__.py
"""

from .base_scraper import BaseScraper

__all__ = ['BaseScraper']


# scrapers/anime/__init__.py
"""
Anime scrapers package - Complete
File: scrapers/anime/__init__.py
"""

from .anidb_scraper import AniDBScraper
from .anilist_scraper import AniListAnimeScraper
from .myanimelist_scraper import MyAnimeListAnimeScraper
from .kitsu_scraper import KitsuAnimeScraper
from .simkl_scraper import SIMKLAnimeScraper
from .animenewsnetwork_scraper import AnimeNewsNetworkScraper
from .animeplanet_scraper import AnimePlanetScraper
from .livechart_scraper import LivechartScraper
from .themoviedb_scraper import TMDBAnimeScraper
from .tvdb_scraper import TVDBScraper
from .imdb_scraper import IMDBScraper

__all__ = [
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
    'IMDBScraper'
]


# scrapers/manga/__init__.py
"""
Manga scrapers package
File: scrapers/manga/__init__.py
"""

from .anilist_scraper import AniListMangaScraper
from .myanimelist_scraper import MyAnimeListMangaScraper
from .kitsu_scraper import KitsuMangaScraper

__all__ = [
    'AniListMangaScraper',
    'MyAnimeListMangaScraper',
    'KitsuMangaScraper'
]
