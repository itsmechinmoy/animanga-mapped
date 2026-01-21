# scrapers/__init__.py
"""
Scrapers package
File: scrapers/__init__.py
"""

from .base_scraper import BaseScraper

__all__ = ['BaseScraper']


# scrapers/anime/__init__.py
"""
Anime scrapers package
File: scrapers/anime/__init__.py
"""

from .anidb_scraper import AniDBScraper
from .anilist_scraper import AniListAnimeScraper
from .myanimelist_scraper import MyAnimeListAnimeScraper
from .kitsu_scraper import KitsuAnimeScraper

__all__ = [
    'AniDBScraper',
    'AniListAnimeScraper',
    'MyAnimeListAnimeScraper',
    'KitsuAnimeScraper'
]


# scrapers/manga/__init__.py
"""
Manga scrapers package
File: scrapers/manga/__init__.py
"""

__all__ = []
