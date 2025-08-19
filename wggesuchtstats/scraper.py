import logging
from typing import Set, Optional

import backoff
from wggesuchtstats import config
from wggesuchtstats.models import FlatAd, FlatAdDetails
from wggesuchtstats.parsers import ListPageParser, DetailPageParser
from wggesuchtstats.util import requests_get

log = logging.getLogger(__name__)
PageRenderError = DetailPageParser.PageRenderError

def find_shared_flats(
    start_page: int = 0, end_page: Optional[int] = None
) -> Set[FlatAd]:
    """
    Scrape flat ads from WG-Gesucht with page range.
    """
    all_ads = set()
    page_num = start_page

    while True:
        if end_page is not None and page_num >= end_page:
            log.info(f"Reached end page limit ({end_page}), stopping.")
            break

        url = f"{config.WG_GESUCHT_BASE_URL}/{config.CITY_PART}.{page_num}.html?pagination=1&pu="
        log.debug(f"Scraping URL: {url}")
        
        try:
            response = requests_get(url)
            if response.status_code != 200:
                log.warning(f"Page {page_num} returned status {response.status_code}, stopping.")
                break

            page_ads = ListPageParser(response.text).parse()
            if not page_ads:
                log.info(f"No more ads found on page {page_num}, stopping.")
                break

            all_ads.update(page_ads)
            log.debug(f"Scraped {len(page_ads)} ads from page {page_num}")
            page_num += 1

        except Exception as e:
            log.error(f"Error scraping page {page_num}: {e}")
            break

    pages_scraped = max(0, page_num - start_page)
    log.info(f"Total ads scraped: {len(all_ads)} from {pages_scraped} pages.")
    return all_ads


def get_flat_details(url: str) -> FlatAdDetails:
    """
    Extract detailed information from a flat ad page, delegating parsing.
    """
    log.debug(f"Fetching details for {url}")
    response = requests_get(url)
    response.raise_for_status()
    
    parser = DetailPageParser(response.text)
    return parser.parse()
