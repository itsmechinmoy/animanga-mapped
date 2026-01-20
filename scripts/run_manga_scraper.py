"""
Execute individual manga scraper
"""
import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scrapers.manga.anilist_scraper import AniListScraper
# Import other manga scrapers

def main():
    parser = argparse.ArgumentParser(description='Run manga scraper')
    parser.add_argument('--service', required=True, 
                       choices=['anilist', 'myanimelist', 'kitsu'])
    args = parser.parse_args()
    
    scrapers = {
        'anilist': lambda: AniListScraper('manga'),
        # Add others...
    }
    
    if args.service not in scrapers:
        print(f"Scraper for {args.service} not implemented yet")
        return
    
    scraper = scrapers[args.service]()
    scraper.run()

if __name__ == '__main__':
    main()
