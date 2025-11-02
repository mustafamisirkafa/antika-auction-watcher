"""Sahibinden.com web scraper with rate limiting."""
import asyncio
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import httpx
from bs4 import BeautifulSoup
from backend.services.marketplace.base_adapter import MarketplaceAdapter
from backend.realtime.redis_manager import RedisManager


class SahibindenScraper(MarketplaceAdapter):
    """
    Sahibinden.com web scraper.
    
    Uses BeautifulSoup for HTML parsing with strict rate limiting.
    Rate limit: 1 request per 2 seconds (self-imposed)
    """

    def __init__(self):
        super().__init__()
        
        # Base URL
        self.base_url = "https://www.sahibinden.com"
        
        # Rate limiting (self-imposed, respectful scraping)
        self.min_request_interval = 2.0  # seconds
        self.last_request_time: Optional[datetime] = None
        
        # Caching (longer TTL for scraped data)
        self.redis_manager = RedisManager()
        self.cache_ttl = 86400  # 24 hours
        
        # User agents for rotation
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
        ]
        self.current_ua_index = 0

    def get_source_name(self) -> str:
        """Get source name."""
        return "sahibinden"

    async def authenticate(self) -> bool:
        """
        No authentication required for public scraping.
        
        Returns:
            Always True
        """
        return True

    async def search_comparables(
        self,
        item_title: str,
        category: str,
        max_results: int = 20,
        **kwargs
    ) -> List[Dict]:
        """
        Scrape Sahibinden for comparable items.
        
        Args:
            item_title: Item title to search for
            category: Item category
            max_results: Maximum results
            **kwargs: Additional parameters
            
        Returns:
            List of comparable items
        """
        # Check cache first (important for scraping)
        cache_key = self.generate_cache_key(item_title, category, **kwargs)
        
        try:
            cached_data = await self.redis_manager.cache_get(cache_key)
            if cached_data:
                import json
                return json.loads(cached_data)
        except Exception:
            pass
        
        # Respect rate limiting
        await self._wait_for_rate_limit()
        
        try:
            results = await self._scrape_listings(item_title, category, max_results)
            
            self.record_request()
            
            # Cache results (long TTL)
            try:
                import json
                await self.redis_manager.cache_set(
                    cache_key,
                    json.dumps(results),
                    self.cache_ttl
                )
            except Exception:
                pass
            
            return results
            
        except Exception as e:
            # Return empty list on scraping errors (don't retry aggressively)
            return []

    async def _wait_for_rate_limit(self):
        """Wait if necessary to respect rate limit."""
        if self.last_request_time:
            elapsed = (datetime.utcnow() - self.last_request_time).total_seconds()
            if elapsed < self.min_request_interval:
                await asyncio.sleep(self.min_request_interval - elapsed)
        
        self.last_request_time = datetime.utcnow()

    async def _scrape_listings(
        self,
        item_title: str,
        category: str,
        max_results: int
    ) -> List[Dict]:
        """
        Scrape Sahibinden listings.
        
        Args:
            item_title: Search query
            category: Item category
            max_results: Max results
            
        Returns:
            List of items
        """
        # Map categories to Sahibinden category IDs
        category_map = {
            'antiques': 'antika',
            'jewelry': 'koleksiyon',
            'collectibles': 'koleksiyon',
            'art': 'resim',
            'furniture': 'mobilya',
            'books': 'kitap'
        }
        
        sahib_category = category_map.get(category.lower(), 'koleksiyon')
        
        # Build search URL
        search_query = item_title.replace(' ', '+')
        search_url = f"{self.base_url}/{sahib_category}?query={search_query}"
        
        # Rotate user agent
        headers = {
            'User-Agent': self.user_agents[self.current_ua_index],
            'Accept': 'text/html,application/xhtml+xml,application/xml',
            'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive'
        }
        self.current_ua_index = (self.current_ua_index + 1) % len(self.user_agents)
        
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            try:
                response = await client.get(search_url, headers=headers)
                response.raise_for_status()
                
                # Parse HTML
                return self._parse_html(response.text, max_results)
                
            except httpx.HTTPError as e:
                raise Exception(f"Sahibinden scraping failed: {str(e)}")

    def _parse_html(self, html: str, max_results: int) -> List[Dict]:
        """
        Parse Sahibinden HTML to extract listings.
        
        Args:
            html: HTML content
            max_results: Max items to return
            
        Returns:
            List of parsed items
        """
        items = []
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Find listing cards (Sahibinden uses <tr class="searchResultsItem">)
            listings = soup.find_all('tr', class_='searchResultsItem', limit=max_results)
            
            for listing in listings:
                try:
                    # Extract title
                    title_elem = listing.find('td', class_='searchResultsTitleValue')
                    title = title_elem.get_text(strip=True) if title_elem else ''
                    
                    # Extract price
                    price_elem = listing.find('td', class_='searchResultsPriceValue')
                    price_text = price_elem.get_text(strip=True) if price_elem else '0'
                    # Remove Turkish Lira symbol and convert
                    price_text = price_text.replace('TL', '').replace('.', '').replace(',', '.').strip()
                    
                    try:
                        price = float(price_text)
                    except ValueError:
                        price = 0.0
                    
                    # Extract location
                    location_elem = listing.find('td', class_='searchResultsLocationValue')
                    location = location_elem.get_text(strip=True) if location_elem else ''
                    
                    # Extract date
                    date_elem = listing.find('td', class_='searchResultsDateValue')
                    date_posted = date_elem.get_text(strip=True) if date_elem else ''
                    
                    # Extract URL
                    link_elem = listing.find('a', class_='classifiedTitle')
                    url = self.base_url + link_elem['href'] if link_elem and 'href' in link_elem.attrs else ''
                    
                    parsed_item = {
                        'title': title,
                        'price': price,
                        'location': location,
                        'date_posted': date_posted,
                        'url': url,
                        'source': 'sahibinden'
                    }
                    
                    # Only add if we have meaningful data
                    if title and price > 0:
                        items.append(parsed_item)
                        
                except Exception as e:
                    # Skip problematic listings
                    continue
                    
        except Exception as e:
            # Return what we've parsed so far
            pass
        
        return items

    async def is_healthy(self) -> bool:
        """Check if scraper is healthy."""
        # Always healthy (no auth required)
        return True
