"""
Base scraper class with common functionality
File: scrapers/base_scraper.py
"""
import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from abc import ABC, abstractmethod

class BaseScraper(ABC):
    """Base class for all service scrapers"""
    
    def __init__(self, service_name: str, media_type: str):
        """
        Initialize base scraper
        
        Args:
            service_name: Name of the service (e.g., 'anilist', 'mal')
            media_type: Type of media ('anime' or 'manga')
        """
        self.service_name = service_name
        self.media_type = media_type
        
        # Import here to avoid circular imports
        from utils.http_utils import RateLimitedSession
        from utils.file_utils import save_json
        
        self.session = RateLimitedSession(self.get_rate_limit())
        self._save_json = save_json
        
        # Setup paths
        self.output_dir = Path(f"scraped-data/{media_type}")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.checkpoint_dir = Path(f"checkpoints/{media_type}")
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        
        self.output_file = self.output_dir / f"{service_name}-{media_type}.json"
        self.checkpoint_file = self.checkpoint_dir / f"{service_name}-checkpoint.json"
        
        # Load checkpoint (with error handling)
        self.checkpoint = self.load_checkpoint()
        
        # Results storage
        self.results: List[Dict[str, Any]] = []
        
        print(f"\n{'='*70}")
        print(f"Initializing {service_name.upper()} scraper for {media_type}")
        print(f"Output: {self.output_file}")
        print(f"{'='*70}\n")
    
    @abstractmethod
    def get_rate_limit(self) -> float:
        """
        Return rate limit in seconds between requests
        
        Returns:
            float: Seconds to wait between requests
        """
        pass
    
    @abstractmethod
    def scrape(self) -> List[Dict[str, Any]]:
        """
        Main scraping logic - must be implemented by each scraper
        
        Returns:
            List of scraped items in standardized format
        """
        pass
    
    @abstractmethod
    def extract_external_ids(self, item: Dict[str, Any]) -> Dict[str, str]:
        """
        Extract external service IDs from item data
        
        Args:
            item: Raw item data from service
            
        Returns:
            Dictionary mapping service names to IDs
        """
        pass
    
    def load_checkpoint(self) -> Dict[str, Any]:
        """
        Load scraping checkpoint with error handling
        
        Returns:
            Checkpoint data dictionary
        """
        default_checkpoint = {
            "last_id": 0,
            "page": 1,
            "offset": 0,
            "last_updated": None
        }
        
        if not self.checkpoint_file.exists():
            return default_checkpoint
        
        try:
            from utils.file_utils import load_json
            checkpoint = load_json(self.checkpoint_file)
            
            # Validate checkpoint has expected structure
            if not isinstance(checkpoint, dict):
                print(f"[WARN] Invalid checkpoint format, using defaults")
                return default_checkpoint
            
            return checkpoint
            
        except (json.JSONDecodeError, Exception) as e:
            print(f"[WARN] Corrupted checkpoint file, starting fresh: {e}")
            # Delete corrupted checkpoint
            try:
                self.checkpoint_file.unlink()
            except:
                pass
            return default_checkpoint
    
    def save_checkpoint(self, data: Dict[str, Any]):
        """
        Save scraping checkpoint
        
        Args:
            data: Checkpoint data to save
        """
        data["last_updated"] = time.strftime("%Y-%m-%d %H:%M:%S")
        self._save_json(self.checkpoint_file, data)
    
    def save_results(self):
        """Save scraped results to file"""
        self._save_json(self.output_file, self.results)
        print(f"\n✓ Saved {len(self.results)} items to {self.output_file}")
    
    def format_item(self, item_id: str, title: str, item_type: str, 
                   external_ids: Dict[str, str], metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format item in standardized structure
        
        Args:
            item_id: Primary ID for this service
            title: Title of the item
            item_type: Type (TV, Movie, OVA, etc.)
            external_ids: Dictionary of external service IDs
            metadata: Additional metadata from service
            
        Returns:
            Standardized item dictionary
        """
        return {
            "id": str(item_id),
            "title": title,
            "type": item_type,
            "external_ids": external_ids,
            "metadata": metadata
        }
    
    def run(self):
        """Execute the scraping process"""
        try:
            print(f"Starting scrape for {self.service_name}...")
            start_time = time.time()
            
            self.results = self.scrape()
            self.save_results()
            
            elapsed = time.time() - start_time
            print(f"\n{'='*70}")
            print(f"{self.service_name.upper()} scraping complete!")
            print(f"Total items: {len(self.results)}")
            print(f"Time elapsed: {elapsed:.2f} seconds")
            print(f"{'='*70}\n")
            
        except KeyboardInterrupt:
            print(f"\n\n[!] Scraping interrupted by user")
            print(f"Saving {len(self.results)} items collected so far...")
            if self.results:
                self.save_results()
            raise
            
        except Exception as e:
            print(f"\n[ERROR] Scraping failed: {e}")
            print(f"Saving {len(self.results)} items collected before error...")
            if self.results:
                self.save_results()
            raise
