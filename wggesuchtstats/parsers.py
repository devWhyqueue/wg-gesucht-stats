import logging
import re
from datetime import datetime, date
from typing import Set, Optional, Tuple

from bs4 import BeautifulSoup, Tag

from wggesuchtstats import config
from wggesuchtstats.models import FlatAd, FlatAdDetails

log = logging.getLogger(__name__)


def _extract_street_from_address(address: Optional[str]) -> Optional[str]:
    """Extract street name from a full address string."""
    if not address:
        return None
    address = re.sub(r"\s+", " ", address.strip())
    # Pattern to match street + optional house number before a 5-digit postal code
    pattern = r"^(.+?)(?=1[0-4]\d{3}\s|$)"
    match = re.match(pattern, address)
    if match:
        street = match.group(1).strip().rstrip(".,")
        return street if street else None
    return None


def _extract_zip_from_address(address: Optional[str]) -> Optional[str]:
    """Extract zip code from a full address string."""
    if not address:
        return None
    address = re.sub(r"\s+", " ", address.strip())
    # Pattern to match Berlin postal codes (10xxx to 14xxx)
    pattern = r"(1[0-4]\d{3})"
    match = re.search(pattern, address)
    return match.group(1) if match else None


# --- Parser for the Search Results (List) Page ---


class ListPageParser:
    """Parses the list of ads on a search results page."""

    def __init__(self, html: str):
        self.soup = BeautifulSoup(html, features="html.parser")
        self.selectors = config.LIST_PAGE_SELECTORS

    def parse(self) -> Set[FlatAd]:
        """Parses all ad rows from the page's HTML."""
        ads = set()
        for row in self.soup.select(self.selectors["ad_row"]):
            try:
                ad = self._parse_single_ad(row)
                if ad:
                    ads.add(ad)
            except Exception as e:
                log.warning(f"Failed to parse ad row: {e}")
                continue
        return ads

    def _parse_single_ad(self, row: Tag) -> Optional[FlatAd]:
        """Parses a single ad from a BeautifulSoup table row element."""
        return FlatAd(
            url=self._extract_url(row),
            published=self._extract_date(row),
            rent=self._extract_rent(row),
            size=self._extract_size(row),
            district=self._extract_district(row),
            female_inhabitants=self._count_inhabitants(row, "weiblich"),
            male_inhabitants=self._count_inhabitants(
                row, "männlich"
            ),  # Corrected from "Mal"
            diverse_inhabitants=self._count_inhabitants(row, "divers"),
            total_inhabitants=self._count_inhabitants(row, ""),
        )

    def _extract_text(self, row: Tag, selector: str) -> str:
        element = row.select_one(selector)
        return element.get_text(strip=True) if element else ""

    def _extract_number(self, row: Tag, selector: str, suffix: str) -> int:
        text = self._extract_text(row, selector)
        return int(text.rstrip(suffix)) if text else 0

    def _extract_date(self, row: Tag) -> datetime:
        date_text = self._extract_text(row, self.selectors["date"])
        return datetime.strptime(date_text, "%d.%m.%Y")

    def _extract_url(self, row: Tag) -> str:
        a = row.select_one(self.selectors["url"])
        return a["href"].strip() if a and a.has_attr("href") else ""

    def _extract_rent(self, row: Tag) -> int:
        return self._extract_number(row, self.selectors["rent"], "€")

    def _extract_size(self, row: Tag) -> int:
        return self._extract_number(row, self.selectors["size"], "m²")

    def _extract_district(self, row: Tag) -> str:
        district = self._extract_text(row, self.selectors["district"])
        district = district.replace("Berlin", "").strip()
        district = re.sub(r"\s+", " ", district)
        return district if district else "Berlin"

    def _count_inhabitants(self, row: Tag, alt_pattern: str) -> int:
        selector = self.selectors["inhabitants_icon"].format(pattern=alt_pattern)
        return len(row.select(selector))


# --- Parser for the Ad Detail Page ---


class DetailPageParser:
    """Parses the detail page of a single flat ad."""

    class PageRenderError(Exception):
        """Custom exception for detail page parsing failures."""

        pass

    def __init__(self, html: str):
        self.soup = BeautifulSoup(html, features="html.parser")
        self.selectors = config.DETAIL_PAGE_SELECTORS

    def parse(self) -> FlatAdDetails:
        """Parses the full ad details from the page's HTML."""
        headline_tags = self.soup.select(self.selectors["headline"])
        if not headline_tags:
            # Ad is no longer online, return empty details object
            return FlatAdDetails()
        headline = headline_tags[0].text.strip()
        if len(headline_tags) > 1:
            headline = headline_tags[1].text.strip()

        description = self._extract_description()
        address = self._extract_address()
        age_min, age_max = self._extract_age_range()

        return FlatAdDetails(
            headline=headline,
            description=description,
            street=_extract_street_from_address(address),
            zip_code=_extract_zip_from_address(address),
            available_from=self._extract_availability_date("frei ab:"),
            available_until=self._extract_availability_date("frei bis:"),
            age_min=age_min,
            age_max=age_max,
        )

    def _extract_description(self) -> str:
        description_divs = self.soup.select(self.selectors["description"])
        return "\n".join([div.text.strip() for div in description_divs])

    def _extract_address(self) -> Optional[str]:
        address_link = self.soup.select_one(self.selectors["address_link"])
        if address_link:
            address_text = address_link.get_text(strip=True)
            return re.sub(r"\s+", " ", address_text)
        return None

    def _extract_availability_date(self, label: str) -> Optional[date]:
        label_span = self.soup.find("span", string=lambda t: t and label in t)
        if label_span and label_span.find_parent("div"):
            sibling_div = label_span.find_parent("div").find_next_sibling("div")
            if sibling_div and sibling_div.find("span"):
                date_text = sibling_div.find("span").get_text(strip=True)
                if re.match(r"\d{2}\.\d{2}\.\d{4}", date_text):
                    return datetime.strptime(date_text, "%d.%m.%Y").date()
        return None

    def _extract_age_range(self) -> Tuple[Optional[int], Optional[int]]:
        age_span = self.soup.find(
            "span", string=lambda t: t and t.startswith("Bewohneralter:")
        )
        if age_span:
            age_text = age_span.get_text()
            match = re.search(r"(\d+)\s*bis\s*(\d+)", age_text)
            if match:
                return int(match.group(1)), int(match.group(2))
            match = re.search(r"(\d+)", age_text)
            if match:
                age = int(match.group(1))
                return age, age
        return None, None
