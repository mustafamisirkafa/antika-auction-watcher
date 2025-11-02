"""Marketplace integrations for real API data."""
from backend.services.marketplace.ebay_client import EbayClient
from backend.services.marketplace.etsy_client import EtsyClient
from backend.services.marketplace.sahibinden_scraper import SahibindenScraper

__all__ = ["EbayClient", "EtsyClient", "SahibindenScraper"]
