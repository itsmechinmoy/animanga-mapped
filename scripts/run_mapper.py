"""
Execute mapping process
File: scripts/run_mapper.py
"""
import sys
import argparse
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mappers.anime_mapper import AnimeMapper
from mappers.manga_mapper import MangaMapper

def main():
    parser = argparse.ArgumentParser(description='Run mapper for anime or manga')
    parser.add_argument(
        '--type',
        required=True,
        choices=['anime', 'manga'],
        help='Type of media to map'
    )
    
    args = parser.parse_args()
    
    try:
        if args.type == 'anime':
            print("Starting anime mapper...")
            mapper = AnimeMapper()
        else:
            print("Starting manga mapper...")
            mapper = MangaMapper()
        
        mapper.run()
        return 0
        
    except KeyboardInterrupt:
        print("\n\n[!] Mapping interrupted by user")
        return 130
    except Exception as e:
        print(f"\n[!] Mapping failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())
