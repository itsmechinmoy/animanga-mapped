"""
Execute individual anime scraper
File: scripts/run_anime_scraper.py
"""
import sys
import argparse
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scrapers.anime.anidb_scraper import AniDBScraper
from scrapers.anime.anilist_scraper import AniListAnimeScraper
from scrapers.anime.myanimelist_scraper import MyAnimeListAnimeScraper
from scrapers.anime.kitsu_scraper import KitsuAnimeScraper

def main():
    parser = argparse.ArgumentParser(description='Run anime scraper for a specific service')
    parser.add_argument(
        '--service',
        required=True,
        choices=[
            'anidb', 'anilist', 'myanimelist', 'kitsu',
            'animenewsnetwork', 'animeplanet', 'livechart',
            'simkl', 'themoviedb', 'tvdb', 'imdb'
        ],
        help='Service to scrape'
    )
    
    args = parser.parse_args()
    
    # Map service to scraper class
    scrapers = {
        'anidb': AniDBScraper,
        'anilist': AniListAnimeScraper,
        'myanimelist': MyAnimeListAnimeScraper,
        'kitsu': KitsuAnimeScraper,
    }
    
    if args.service not in scrapers:
        print(f"[!] Scraper for {args.service} not implemented yet")
        print(f"[!] Available scrapers: {', '.join(scrapers.keys())}")
        return 1
    
    try:
        scraper = scrapers[args.service]()
        scraper.run()
        return 0
    except KeyboardInterrupt:
        print("\n\n[!] Scraper interrupted by user")
        return 130
    except Exception as e:
        print(f"\n[!] Scraper failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())
