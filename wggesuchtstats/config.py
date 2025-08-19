# --- General Configuration ---
WG_GESUCHT_BASE_URL = "https://www.wg-gesucht.de"
CITY_PART = "wg-zimmer-in-Berlin.8.0.0"

# --- CSS Selectors for the Ad List Page ---
LIST_PAGE_SELECTORS = {
    "ad_row": "tr.offer_list_item",
    "date": "td.ang_spalte_datum span",
    "url": "td.ang_spalte_datum a",
    "rent": "td.ang_spalte_miete b",
    "size": "td.ang_spalte_groesse span",
    "district": "td.ang_spalte_stadt span",
    "inhabitants_icon": 'td.ang_spalte_icons img[alt*="{pattern}"]',
}

# --- CSS Selectors for the Ad Detail Page ---
DETAIL_PAGE_SELECTORS = {
    "headline": ".detailed-view-title span[class]",
    "description": "div[id^='freitext']",
    "address_link": 'a[href="#map_container"]',
}

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
]