"""
Base scraper class with common functionality
"""
import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from abc import ABC, abstractmethod
from utils.http_utils import RateLimitedSession
from utils.file_utils import save_json, load_json

class BaseScraper(ABC):
    """Base class for all service scrapers"""
    
    def __init__(self, service_name: str, media_type: str):
        self.service_name = service_name
        self.media_type = media_type
        self.session = RateLimitedSession(self.get_rate_limit())
        
        # Setup paths
        self.output_dir = Path(f"scraped-data/{media_type}")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.checkpoint_dir = Path(f"checkpoints/{media_type}")
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        
        self.output_file = self.output_dir / f"{service_name}-{media_type}.json"
        self.checkpoint_file = self.checkpoint_dir / f"{service_name}-checkpoint.json"
        
        # Load checkpoint
        self.checkpoint = self.load_checkpoint()
        
        # Results storage
        self.results: List[Dict[str, Any]] = []
        
        print(f"\n{'='*70}")
        print(f"Initializing {service_name.upper()} scraper for {media_type}")
        print(f"Output: {self.output_file}")
        print(f"{'='*70}\n")
    
    @abstractmethod
    def get_rate_limit(self) -> float:
        """Return rate limit in seconds between requests"""
        pass
    
    @abstractmethod
    def scrape(self) -> List[Dict[str, Any]]:
        """Main scraping logic - must be implemented by each scraper"""
        pass
    
    @abstractmethod
    def extract_external_ids(self, item: Dict[str, Any]) -> Dict[str, str]:
        """Extract external service IDs from item data"""
        pass
    
    def load_checkpoint(self) -> Dict[str, Any]:
        """Load scraping checkpoint"""
        if self.checkpoint_file.exists():
            return load_json(self.checkpoint_file)
        return {"last_id": 0, "page": 1, "offset": 0}
    
    def save_checkpoint(self, data: Dict[str, Any]):
        """Save scraping checkpoint"""
        save_json(self.checkpoint_file, data)
    
    def save_results(self):
        """Save scraped results to file"""
        save_json(self.output_file, self.results)
        print(f"\n✓ Saved {len(self.results)} items to {self.output_file}")
    
    def format_item(self, item_id: str, title: str, item_type: str, 
                   external_ids: Dict[str, str], metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Format item in standardized structure"""
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
            self.results = self.scrape()
            self.save_results()
            print(f"\n{'='*70}")
            print(f"{self.service_name.upper()} scraping complete!")
            print(f"Total items: {len(self.results)}")
            print(f"{'='*70}\n")
        except Exception as e:
            print(f"\n[ERROR] Scraping failed: {e}")
            raise
