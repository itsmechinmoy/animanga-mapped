"""
Execute mapping process
"""
import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from mappers.anime_mapper import AnimeMapper
from mappers.manga_mapper import MangaMapper

def main():
    parser = argparse.ArgumentParser(description='Run mapper')
    parser.add_argument('--type', required=True, choices=['anime', 'manga'])
    args = parser.parse_args()
    
    if args.type == 'anime':
        mapper = AnimeMapper()
    else:
        mapper = MangaMapper()
    
    mapper.run()

if __name__ == '__main__':
    main()
