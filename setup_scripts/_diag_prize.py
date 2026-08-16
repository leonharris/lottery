#!/usr/bin/env python3
"""Temporary diagnostic: dump exact row/cell structure of the prize table."""
import requests
from bs4 import BeautifulSoup

HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; lottery-data-fetcher/1.0)'}


def dump_table(url):
    r = requests.get(url, timeout=15, headers=HEADERS)
    r.raise_for_status()
    soup = BeautifulSoup(r.content, 'html.parser')
    tables = soup.find_all('table')
    t = tables[1]
    print(f"table classes={t.get('class')}")
    for i, tr in enumerate(t.find_all('tr')):
        cells = tr.find_all(['th', 'td'])
        cell_reprs = []
        for c in cells:
            classes = c.get('class')
            cell_reprs.append(f"[{c.name}{'.' + '.'.join(classes) if classes else ''}]{c.get_text('|', strip=True)!r}")
        print(f"  row[{i}] ({len(cells)} cells): {cell_reprs}")


if __name__ == '__main__':
    print("===== LOTTO (03-01-2026, has a rollover row) =====")
    dump_table('https://www.lottery.co.uk/lotto/results-03-01-2026')
    print("\n===== LOTTO (recent, likely no rollover) =====")
    dump_table('https://www.lottery.co.uk/lotto/results-15-08-2026')
    print("\n===== EUROMILLIONS (02-01-2026, has a rollover row) =====")
    dump_table('https://www.lottery.co.uk/euromillions/results-02-01-2026')
