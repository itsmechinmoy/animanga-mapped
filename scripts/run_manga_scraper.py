"""
Execute individual manga scraper
File: scripts/run_manga_scraper.py
"""
import sys
import argparse
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scrapers.manga.anilist_scraper import AniListMangaScraper
from scrapers.manga.myanimelist_scraper import MyAnimeListMangaScraper
from scrapers.manga.kitsu_scraper import KitsuMangaScraper

def main():
    parser = argparse.ArgumentParser(description='Run manga scraper for a specific service')
    parser.add_argument(
        '--service',
        required=True,
        choices=['anilist', 'myanimelist', 'kitsu'],
        help='Service to scrape'
    )
    
    args = parser.parse_args()
    
    # Map service to scraper class
    scrapers = {
        'anilist': AniListMangaScraper,
        'myanimelist': MyAnimeListMangaScraper,
        'kitsu': KitsuMangaScraper,
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
