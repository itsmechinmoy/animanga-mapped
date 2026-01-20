"""
HTTP utilities with rate limiting
"""
import time
import requests
from typing import Optional

class RateLimitedSession:
    """HTTP session with automatic rate limiting"""
    
    def __init__(self, rate_limit: float = 1.0):
        self.rate_limit = rate_limit
        self.last_request = 0
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'AnimeMangaMapper/1.0 (https://github.com/yourusername/animanga-mapped)'
        })
    
    def _wait(self):
        """Wait for rate limit"""
        elapsed = time.time() - self.last_request
        if elapsed < self.rate_limit:
            time.sleep(self.rate_limit - elapsed)
        self.last_request = time.time()
    
    def get(self, url: str, **kwargs):
        """GET request with rate limiting"""
        self._wait()
        return self.session.get(url, **kwargs)
    
    def post(self, url: str, **kwargs):
        """POST request with rate limiting"""
        self._wait()
        return self.session.post(url, **kwargs)
