"""
IMDB scraper (uses public datasets)
File: scrapers/anime/imdb_scraper.py
"""
from typing import Dict, List, Any
import sys
from pathlib import Path
import gzip
import csv
import io

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scrapers.base_scraper import BaseScraper

class IMDBScraper(BaseScraper):
    """
    Scraper for IMDB using their public datasets
    https://datasets.imdbws.com/
    """
    
    # IMDB provides public datasets as TSV files
    TITLE_BASICS_URL = "https://datasets.imdbws.com/title.basics.tsv.gz"
    
    def __init__(self):
        super().__init__("imdb", "anime")
    
    def get_rate_limit(self) -> float:
        return 1.0
    
    def scrape(self) -> List[Dict[str, Any]]:
        """
        Scrape IMDB data from public datasets
        We'll download title.basics and filter for anime
        """
        print("Downloading IMDB public dataset...")
        print("This is a large file (~250MB compressed)")
        print("Download may take several minutes\n")
        
        results = []
        
        try:
            # Download the dataset
            response = self.session.get(self.TITLE_BASICS_URL, stream=True)
            
            if response.status_code != 200:
                print(f"[!] Failed to download IMDB dataset: {response.status_code}")
                return results
            
            print("✓ Downloaded successfully")
            print("Processing dataset (this will take a while)...\n")
            
            # Decompress and process line by line
            with gzip.GzipFile(fileobj=io.BytesIO(response.content)) as gz:
                # Read as text
                text_content = gz.read().decode('utf-8')
                
                # Parse TSV
                reader = csv.DictReader(
                    io.StringIO(text_content),
                    delimiter='\t',
                    quoting=csv.QUOTE_NONE
                )
                
                count = 0
                anime_count = 0
                
                for row in reader:
                    count += 1
                    
                    if count % 100000 == 0:
                        print(f"  Processed {count:,} titles, found {anime_count:,} anime...")
                    
                    # Filter for anime
                    # Look for Japanese titles with animation genre
                    genres = row.get('genres', '')
                    
                    if 'Animation' not in genres:
                        continue
                    
                    # Check if it's likely anime (Japanese origin)
                    original_title = row.get('originalTitle', '')
                    title_type = row.get('titleType', '')
                    
                    # Basic heuristic for anime
                    # This is imperfect but catches most anime
                    is_anime = False
                    
                    # Check genres includes Animation
                    if 'Animation' in genres:
                        # Check if TV series or movie
                        if title_type in ['tvSeries', 'tvMiniSeries', 'movie', 'tvSpecial']:
                            is_anime = True
                    
                    if not is_anime:
                        continue
                    
                    try:
                        processed = self.process_item(row)
                        if processed:
                            results.append(processed)
                            anime_count += 1
                    except Exception as e:
                        continue
            
            print(f"\n✓ Processed {count:,} total titles")
            print(f"✓ Found {len(results):,} anime")
            
        except Exception as e:
            print(f"[ERROR] Failed to process IMDB dataset: {e}")
        
        return results
    
    def process_item(self, row: Dict[str, str]) -> Dict[str, Any]:
        """Process IMDB dataset row"""
        imdb_id = row.get('tconst', '')
        
        if not imdb_id:
            return None
        
        title = row.get('primaryTitle', f"Unknown {imdb_id}")
        item_type = row.get('titleType', '').upper()
        
        # External IDs
        external_ids = {'imdb': imdb_id}
        
        # Metadata
        metadata = {
            "primary_title": row.get('primaryTitle'),
            "original_title": row.get('originalTitle'),
            "is_adult": row.get('isAdult') == '1',
            "start_year": row.get('startYear'),
            "end_year": row.get('endYear'),
            "runtime_minutes": row.get('runtimeMinutes'),
            "genres": row.get('genres', '').split(',') if row.get('genres') != '\\N' else []
        }
        
        return self.format_item(imdb_id, title, item_type, external_ids, metadata)
    
    def extract_external_ids(self, item: Dict[str, Any]) -> Dict[str, str]:
        """IMDB doesn't provide external IDs directly"""
        return {}
