"""
HTTP utilities with rate limiting and retry logic
File: utils/http_utils.py
"""
import time
import requests
from typing import Optional, Dict, Any
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

class RateLimitedSession:
    """HTTP session with automatic rate limiting and retries"""
    
    def __init__(self, rate_limit: float = 1.0):
        """
        Initialize rate-limited session
        
        Args:
            rate_limit: Minimum seconds between requests
        """
        self.rate_limit = rate_limit
        self.last_request = 0
        
        # Create session with retry strategy
        self.session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "POST", "PUT", "DELETE", "OPTIONS", "TRACE"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Set default headers
        self.session.headers.update({
            'User-Agent': 'AnimeMangaMapper/1.0 (https://github.com/itsmechinmoy/animanga-mapped)'
        })
    
    def _wait(self):
        """Wait for rate limit if necessary"""
        elapsed = time.time() - self.last_request
        if elapsed < self.rate_limit:
            sleep_time = self.rate_limit - elapsed
            time.sleep(sleep_time)
        self.last_request = time.time()
    
    def get(self, url: str, **kwargs) -> requests.Response:
        """
        GET request with rate limiting
        
        Args:
            url: URL to request
            **kwargs: Additional arguments to pass to requests.get
            
        Returns:
            Response object
        """
        self._wait()
        
        # Set default timeout if not provided
        if 'timeout' not in kwargs:
            kwargs['timeout'] = 30
        
        try:
            response = self.session.get(url, **kwargs)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            print(f"  [!] Request failed for {url}: {e}")
            raise
    
    def post(self, url: str, **kwargs) -> requests.Response:
        """
        POST request with rate limiting
        
        Args:
            url: URL to request
            **kwargs: Additional arguments to pass to requests.post
            
        Returns:
            Response object
        """
        self._wait()
        
        # Set default timeout if not provided
        if 'timeout' not in kwargs:
            kwargs['timeout'] = 30
        
        try:
            response = self.session.post(url, **kwargs)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            print(f"  [!] Request failed for {url}: {e}")
            raise
    
    def close(self):
        """Close the session"""
        self.session.close()
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
