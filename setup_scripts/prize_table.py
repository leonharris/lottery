"""Shared prize-breakdown scraper for lottery.co.uk individual draw pages.

Used by scrape_lotto.py / scrape_euromillions.py to fetch the real £ prize
per winner for each tier of a *newly seen* draw (not for historical
backfill — we only start tracking money from when this feature shipped).
"""
import requests
from bs4 import BeautifulSoup

HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; lottery-data-fetcher/1.0)'}

LOTTO_TICKET_PRICE = 2.00
EM_TICKET_PRICE = 2.50

# lottery.co.uk category text (lowercased) -> our tier key
LOTTO_TIER_MAP = {
    'match 6': '6',
    'match 5 plus bonus': '5+bonus',
    'match 5': '5',
    'match 4': '4',
    'match 3': '3',
    'match 2': '2',
}

EM_TIER_MAP = {
    'match 5 and 2 stars': '5-2',
    'match 5 and 1 star': '5-1',
    'match 5': '5-0',
    'match 4 and 2 stars': '4-2',
    'match 4 and 1 star': '4-1',
    'match 3 and 2 stars': '3-2',
    'match 4': '4-0',
    'match 2 and 2 stars': '2-2',
    'match 3 and 1 star': '3-1',
    'match 3': '3-0',
    'match 1 and 2 stars': '1-2',
    'match 2 and 1 star': '2-1',
    'match 2': '2-0',
}


def _parse_amount(text, ticket_price):
    text = text.strip()
    if text in ('-', ''):
        return 0.0
    if 'free ticket' in text.lower():
        return ticket_price
    cleaned = text.replace('£', '').replace(',', '')
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def _find_col_indices(header_cells):
    texts = [c.get_text(strip=True).lower() for c in header_cells]
    prize_idx = next((i for i, t in enumerate(texts) if 'prize' in t and 'fund' not in t), None)
    return prize_idx


def fetch_prize_table(detail_url, tier_map, ticket_price):
    """Returns {tier_key: amount} for the tiers we recognise on this draw's page.

    A tier with zero real winners (rollover) still lists the amount a
    winning line *would* receive that draw before it rolls over, so we
    keep that listed amount rather than zeroing it out.
    """
    if detail_url.startswith('/'):
        detail_url = 'https://www.lottery.co.uk' + detail_url
    r = requests.get(detail_url, timeout=15, headers=HEADERS)
    r.raise_for_status()
    soup = BeautifulSoup(r.content, 'html.parser')

    table = None
    for t in soup.find_all('table'):
        headers = [th.get_text(strip=True).lower() for th in t.find_all('th')]
        if 'category' in headers:
            table = t
            break
    if table is None:
        return {}

    rows = table.find_all('tr')
    if not rows:
        return {}
    header_cells = rows[0].find_all(['th', 'td'])
    prize_idx = _find_col_indices(header_cells)
    if prize_idx is None:
        return {}

    prizes = {}
    for tr in rows[1:]:
        cells = tr.find_all(['th', 'td'])
        if not cells or prize_idx >= len(cells):
            continue
        category = cells[0].get_text(strip=True)
        if category.lower() == 'totals':
            continue
        key = tier_map.get(category.lower())
        if key is None:
            continue
        prizes[key] = _parse_amount(cells[prize_idx].get_text(strip=True), ticket_price)
    return prizes
