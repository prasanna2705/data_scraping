"""Scraper package: adapters for Amazon, Flipkart, OnePlus, and resolution helpers."""

from scraper.manager import collect_url, run_scrape, validate_source
from scraper.resolver import resolve_query

__all__ = ["collect_url", "run_scrape", "validate_source", "resolve_query"]
