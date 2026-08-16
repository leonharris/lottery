#!/usr/bin/env python3
"""Temporary diagnostic: inspect an individual draw results page for prize-table markup."""
import re
import requests
from bs4 import BeautifulSoup

HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; lottery-data-fetcher/1.0)'}


def inspect(game, archive_url, link_substr):
    print(f"\n===== {game} =====")
    r = requests.get(archive_url, timeout=15, headers=HEADERS)
    r.raise_for_status()
    soup = BeautifulSoup(r.content, 'html.parser')
    links = [a['href'] for a in soup.find_all('a', href=lambda h: h and link_substr in h)]
    print(f"Found {len(links)} draw links. Last few: {links[-3:]}")
    if not links:
        return
    detail_url = links[-1]
    if detail_url.startswith('/'):
        detail_url = 'https://www.lottery.co.uk' + detail_url
    print(f"Fetching detail page: {detail_url}")
    r2 = requests.get(detail_url, timeout=15, headers=HEADERS)
    r2.raise_for_status()
    soup2 = BeautifulSoup(r2.content, 'html.parser')

    for kw in ('Dividend', 'Prize', 'Winners', 'Rollover', 'Match'):
        els = soup2.find_all(string=re.compile(kw, re.I))
        print(f"  '{kw}' text occurrences: {len(els)}")

    tables = soup2.find_all('table')
    print(f"  <table> count: {len(tables)}")
    for i, t in enumerate(tables):
        txt = t.get_text(' ', strip=True)[:200]
        print(f"  table[{i}] classes={t.get('class')} preview={txt}")

    for kw in ('prize', 'dividend', 'winner', 'breakdown'):
        els = soup2.find_all(class_=lambda c: c and kw in ' '.join(c).lower())
        print(f"  class~={kw}: {len(els)} elements")
        for el in els[:3]:
            print(f"    <{el.name} class={el.get('class')}> {el.get_text(' ', strip=True)[:300]}")


if __name__ == '__main__':
    import datetime
    year = datetime.datetime.now().year
    inspect('LOTTO', f'https://www.lottery.co.uk/lotto/results/archive-{year}', '/lotto/results-')
    inspect('EUROMILLIONS', f'https://www.lottery.co.uk/euromillions/results/archive-{year}', '/euromillions/results-')
