#!/usr/bin/env python3
"""
EuroMillions Historical Data Scraper
Fetches results from lottery.co.uk (2004–present)

Usage:
  python scrape_euromillions.py           # Full history scrape
  python scrape_euromillions.py --update  # Append latest draws only
"""

import json
import os
import re
import sys
import time
from datetime import datetime

import requests
from bs4 import BeautifulSoup

OUTPUT_FILE = os.path.join(os.path.dirname(__file__), '../assets/data/euromillions-results.json')
LOTTO_FILE = os.path.join(os.path.dirname(__file__), '../assets/data/lotto-results.json')
FREQ_JSON_FILE = os.path.join(os.path.dirname(__file__), '../assets/data/frequency-data.json')
FREQ_JS_FILE = os.path.join(os.path.dirname(__file__), '../assets/js/frequency-data.js')
HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; lottery-data-fetcher/1.0)'}


def parse_row(row):
    try:
        date_link = row.find('a', href=lambda h: h and '/euromillions/results-' in h)
        if not date_link:
            return None

        date_text = date_link.get_text(strip=True)
        clean_date = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', date_text)
        draw_date = None
        for fmt in ('%A %d %B %Y', '%A %d %b %Y'):
            try:
                draw_date = datetime.strptime(clean_date, fmt)
                break
            except ValueError:
                continue
        if draw_date is None:
            return None

        # lottery.co.uk uses <div class="result small euromillions-ball"> for main balls
        # and <div class="result small euromillions-lucky-star"> for lucky stars
        main_balls = []
        lucky_stars = []

        for div in row.find_all('div', class_='result'):
            classes = ' '.join(div.get('class', []))
            try:
                num = int(div.get_text(strip=True))
            except ValueError:
                continue
            if 'lucky-star' in classes:
                lucky_stars.append(num)
            elif 'euromillions-ball' in classes:
                main_balls.append(num)

        if len(main_balls) != 5 or len(lucky_stars) != 2:
            return None
        if not all(1 <= b <= 50 for b in main_balls):
            return None
        if not all(1 <= s <= 12 for s in lucky_stars):
            return None

        return {
            "date": draw_date.strftime('%Y-%m-%d'),
            "day": draw_date.strftime('%a'),
            "b": sorted(main_balls),
            "s": sorted(lucky_stars),
        }
    except Exception:
        return None


def fetch_year(year):
    url = f"https://www.lottery.co.uk/euromillions/results/archive-{year}"
    print(f"  {year}...", end=" ", flush=True)
    try:
        r = requests.get(url, timeout=15, headers=HEADERS)
        r.raise_for_status()
        soup = BeautifulSoup(r.content, 'html.parser')
        draws = [d for row in soup.find_all('tr') if (d := parse_row(row))]
        print(f"✓ {len(draws)}")
        return draws
    except Exception as e:
        print(f"✗ {e}")
        return []


def load_existing():
    try:
        with open(OUTPUT_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save(draws):
    seen, unique = set(), []
    for d in sorted(draws, key=lambda x: x['date']):
        if d['date'] not in seen:
            seen.add(d['date'])
            unique.append(d)
    os.makedirs(os.path.dirname(os.path.abspath(OUTPUT_FILE)), exist_ok=True)
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(unique, f, separators=(',', ':'))
    return unique


def compute_top_n(freq, n):
    sorted_items = sorted(freq.items(), key=lambda x: -x[1])
    cutoff = sorted_items[n - 1][1] if len(sorted_items) >= n else 0
    return [num for num, count in sorted_items if count >= cutoff]


def generate_frequency_js():
    try:
        with open(OUTPUT_FILE) as f:
            em_draws = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        em_draws = []

    try:
        with open(LOTTO_FILE) as f:
            lotto_draws = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        lotto_draws = []

    em_balls = {i: 0 for i in range(1, 51)}
    em_stars = {i: 0 for i in range(1, 13)}
    for d in em_draws:
        for b in d['b']: em_balls[b] += 1
        for s in d['s']: em_stars[s] += 1

    lotto = {i: 0 for i in range(1, 60)}
    for d in lotto_draws:
        for n in d['draw_result'].split(','):
            lotto[int(n)] += 1

    data = {
        "generated": datetime.now().strftime('%Y-%m-%d'),
        "em_draws": len(em_draws),
        "lotto":    {"freq": lotto,    "topN": compute_top_n(lotto, 6)},
        "em_balls": {"freq": em_balls, "topN": compute_top_n(em_balls, 5)},
        "em_stars": {"freq": em_stars, "topN": compute_top_n(em_stars, 2)},
    }

    # Pure JSON file — fetched by the browser sync button
    with open(FREQ_JSON_FILE, 'w') as f:
        json.dump(data, f, separators=(',', ':'))

    # JS wrapper — loaded synchronously for file:// compatibility
    with open(FREQ_JS_FILE, 'w') as f:
        f.write('// Auto-generated by scrape_euromillions.py — do not edit\n')
        f.write(f'const FREQ_JSON={json.dumps(data, separators=(",", ":"))};' + '\n')

    print(f"Frequency data written → {FREQ_JSON_FILE} + {FREQ_JS_FILE}")


def full_scrape():
    print("EuroMillions full history scrape (2004–present)\n")
    all_draws = []
    for year in range(2004, datetime.now().year + 1):
        all_draws.extend(fetch_year(year))
        time.sleep(1)
    result = save(all_draws)
    print(f"\nSaved {len(result)} draws → {OUTPUT_FILE}")
    generate_frequency_js()


def update_scrape():
    existing = load_existing()
    latest = existing[-1]['date'] if existing else '2004-01-01'
    print(f"Update mode — latest on record: {latest}")
    current_year = datetime.now().year
    years = [current_year] if datetime.now().month > 1 else [current_year - 1, current_year]
    new_draws = []
    for year in years:
        new_draws.extend(fetch_year(year))
        time.sleep(1)
    combined = existing + [d for d in new_draws if d['date'] > latest]
    result = save(combined)
    print(f"Added {len(result) - len(existing)} new draw(s). Total: {len(result)}")
    generate_frequency_js()


if __name__ == '__main__':
    try:
        import requests
        from bs4 import BeautifulSoup
    except ImportError:
        print("pip install requests beautifulsoup4")
        sys.exit(1)

    if '--update' in sys.argv:
        update_scrape()
    else:
        full_scrape()
