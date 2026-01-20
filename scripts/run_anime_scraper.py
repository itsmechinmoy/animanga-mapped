"""
Execute individual anime scraper
"""
import sys
import argparse
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scrapers.anime.anidb_scraper import AniDBScraper
from scrapers.anime.anilist_scraper import AniListScraper
# Import other scrapers as needed

def main():
    parser = argparse.ArgumentParser(description='Run anime scraper')
    parser.add_argument('--service', required=True, 
                       choices=['anidb', 'anilist', 'myanimelist', 'kitsu', 
                               'animenewsnetwork', 'animeplanet', 'livechart',
                               'simkl', 'themoviedb', 'tvdb', 'imdb'])
    args = parser.parse_args()
    
    # Map service to scraper class
    scrapers = {
        'anidb': AniDBScraper,
        'anilist': lambda: AniListScraper('anime'),
        # Add others...
    }
    
    if args.service not in scrapers:
        print(f"Scraper for {args.service} not implemented yet")
        return
    
    scraper = scrapers[args.service]()
    scraper.run()

if __name__ == '__main__':
    main()
