#!/usr/bin/env python3
"""
UK Lotto Historical Data Scraper
Fetches real results from lottery.co.uk (59-ball format, 10 Oct 2015–present)

Usage:
  python scrape_lotto.py           # Full history scrape (replaces the file)
  python scrape_lotto.py --update  # Append latest draws only
"""

import json
import os
import random
import re
import sys
import time
from datetime import datetime

import requests
from bs4 import BeautifulSoup

OUTPUT_FILE = os.path.join(os.path.dirname(__file__), '../assets/data/lotto-results.json')
EM_FILE = os.path.join(os.path.dirname(__file__), '../assets/data/euromillions-results.json')
FREQ_JSON_FILE = os.path.join(os.path.dirname(__file__), '../assets/data/frequency-data.json')
FREQ_JS_FILE = os.path.join(os.path.dirname(__file__), '../assets/js/frequency-data.js')
HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; lottery-data-fetcher/1.0)'}
FORMAT_START = datetime(2015, 10, 10)  # 59-ball format introduced this date


def parse_date(row):
    date_link = row.find('a', href=lambda h: h and '/lotto/results-' in h)
    if not date_link:
        return None
    date_text = date_link.get_text(strip=True)
    clean_date = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', date_text)
    for fmt in ('%A %d %B %Y', '%A %d %b %Y'):
        try:
            return datetime.strptime(clean_date, fmt)
        except ValueError:
            continue
    return None


def extract_via_divs(row):
    """Site markup style seen on the EuroMillions pages: one div per ball.

    Draws from late July 2026 onwards carry a second "Round 2" number set
    (lotto-ball-round-2 / lotto-bonus-ball-round-2); only Round 1 is the
    primary draw this app models, so Round 2 divs are skipped.
    """
    main_balls, bonus = [], None
    for div in row.find_all('div', class_='result'):
        classes = ' '.join(div.get('class', []))
        if 'round-2' in classes:
            continue
        try:
            num = int(div.get_text(strip=True))
        except ValueError:
            continue
        if 'bonus' in classes:
            bonus = num
        elif 'lotto-ball' in classes or 'ball' in classes:
            main_balls.append(num)
    return main_balls, bonus


def extract_via_text_cell(row):
    """Fallback: a single results cell containing all numbers as plain text."""
    cell = row.find('td', class_='results') or row.find('td', class_=lambda c: c and 'result' in c)
    if not cell:
        return [], None
    text = cell.get_text(' ', strip=True).split('There were')[0]
    numbers = [int(n) for n in re.findall(r'\b(\d{1,2})\b', text) if 1 <= int(n) <= 59]
    if len(numbers) < 7:
        return [], None
    return numbers[:6], numbers[6]


def parse_row(row):
    try:
        draw_date = parse_date(row)
        if draw_date is None or draw_date < FORMAT_START:
            return None

        main_balls, bonus = extract_via_divs(row)
        if len(main_balls) != 6 or bonus is None:
            main_balls, bonus = extract_via_text_cell(row)

        if len(main_balls) != 6 or bonus is None:
            return None
        if len(set(main_balls)) != 6 or not all(1 <= b <= 59 for b in main_balls):
            return None
        if not 1 <= bonus <= 59:
            return None

        return {
            "draw_number": None,
            "draw_date": draw_date.strftime('%Y-%m-%d'),
            "draw_day": draw_date.strftime('%a'),
            "draw_result": ','.join(str(n) for n in main_balls),
            "bonus_ball": bonus,
        }
    except Exception:
        return None


def fetch_url(url, label):
    print(f"  {label}...", end=" ", flush=True)
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


def fetch_year(year):
    return fetch_url(f"https://www.lottery.co.uk/lotto/results/archive-{year}", str(year))


def load_existing():
    try:
        with open(OUTPUT_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def renumber(draws):
    # Official draw numbers aren't reliably scrapable from the results table;
    # assign sequential numbers ordered by date so downstream consumers still
    # have a stable, monotonic draw_number.
    for i, d in enumerate(sorted(draws, key=lambda x: x['draw_date']), start=1):
        d['draw_number'] = i
    return draws


def save(draws):
    seen, unique = set(), []
    for d in sorted(draws, key=lambda x: x['draw_date']):
        if d['draw_date'] not in seen:
            seen.add(d['draw_date'])
            unique.append(d)
    unique = renumber(unique)
    os.makedirs(os.path.dirname(os.path.abspath(OUTPUT_FILE)), exist_ok=True)
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(unique, f, separators=(',', ':'))
    return unique


def compute_top_n(freq, n):
    # Ties that fit entirely within the top n carry through together (no
    # ambiguity there). Only a tie group straddling the final slot(s) needs
    # a random pick to fill the remaining space.
    groups = {}
    for num, count in freq.items():
        groups.setdefault(count, []).append(num)

    result = []
    for count in sorted(groups, reverse=True):
        group = sorted(groups[count])
        remaining = n - len(result)
        if len(group) <= remaining:
            result.extend(group)
        else:
            result.extend(random.sample(group, remaining))
        if len(result) >= n:
            break
    return result


def generate_frequency_js():
    try:
        with open(EM_FILE) as f:
            em_draws = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        em_draws = []

    try:
        with open(OUTPUT_FILE) as f:
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

    with open(FREQ_JSON_FILE, 'w') as f:
        json.dump(data, f, separators=(',', ':'))

    with open(FREQ_JS_FILE, 'w') as f:
        f.write('// Auto-generated by scrape_lotto.py / scrape_euromillions.py — do not edit\n')
        f.write(f'const FREQ_JSON={json.dumps(data, separators=(",", ":"))};' + '\n')

    print(f"Frequency data written → {FREQ_JSON_FILE} + {FREQ_JS_FILE}")


def full_scrape():
    print("UK Lotto full history scrape (10 Oct 2015–present)\n")
    all_draws = []
    for year in range(2015, datetime.now().year + 1):
        all_draws.extend(fetch_year(year))
        time.sleep(1)
    result = save(all_draws)
    print(f"\nSaved {len(result)} draws → {OUTPUT_FILE}")
    generate_frequency_js()


def update_scrape():
    existing = load_existing()
    latest = existing[-1]['draw_date'] if existing else '2015-10-10'
    print(f"Update mode — latest on record: {latest}")
    current_year = datetime.now().year
    years = [current_year] if datetime.now().month > 1 else [current_year - 1, current_year]
    new_draws = []
    for year in years:
        new_draws.extend(fetch_year(year))
        time.sleep(1)
    combined = existing + [d for d in new_draws if d['draw_date'] > latest]
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
