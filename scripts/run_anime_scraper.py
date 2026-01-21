"""
Execute individual anime scraper - Complete
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
from scrapers.anime.simkl_scraper import SIMKLAnimeScraper
from scrapers.anime.animenewsnetwork_scraper import AnimeNewsNetworkScraper
from scrapers.anime.animeplanet_scraper import AnimePlanetScraper
from scrapers.anime.livechart_scraper import LivechartScraper
from scrapers.anime.themoviedb_scraper import TMDBAnimeScraper
from scrapers.anime.tvdb_scraper import TVDBScraper
from scrapers.anime.imdb_scraper import IMDBScraper

def main():
    parser = argparse.ArgumentParser(description='Run anime scraper for a specific service')
    parser.add_argument(
        '--service',
        required=True,
        choices=[
            'anidb', 'anilist', 'myanimelist', 'kitsu',
            'simkl', 'animenewsnetwork', 'animeplanet',
            'livechart', 'themoviedb', 'tvdb', 'imdb'
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
        'simkl': SIMKLAnimeScraper,
        'animenewsnetwork': AnimeNewsNetworkScraper,
        'animeplanet': AnimePlanetScraper,
        'livechart': LivechartScraper,
        'themoviedb': TMDBAnimeScraper,
        'tvdb': TVDBScraper,
        'imdb': IMDBScraper,
    }
    
    if args.service not in scrapers:
        print(f"[!] Scraper for {args.service} not found")
        print(f"[!] Available scrapers: {', '.join(scrapers.keys())}")
        return 1
    
    try:
        print(f"\n{'='*70}")
        print(f"STARTING {args.service.upper()} SCRAPER")
        print(f"{'='*70}\n")
        
        scraper = scrapers[args.service]()
        scraper.run()
        
        print(f"\n{'='*70}")
        print(f"✓✓✓ {args.service.upper()} SCRAPER COMPLETED SUCCESSFULLY")
        print(f"{'='*70}\n")
        
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
