#!/usr/bin/env python3
"""
Weekly draw report: generates 10 random + 10 weighted + 1 top-N line per
game, scores them against the most recent unreported real draw, and prints
one ready-to-send email per (game, draw) as JSON:
  {"reports": [{"game", "subject", "text", "html"}, ...]}

One draw = one email: a `reports/ledger.json` file (not linked from the
site — kept out of assets/ so casual visitors never see it) tracks the
last draw date already reported per game, so a draw is only ever included
once, and running year-to-date cost-vs-winnings totals are kept separately
per generation mode (random / weighted / top N).

The frequency tables used for weighted/top-N generation are built from all
draws *before* the target draw, so the target draw's own result can't leak
into the numbers used to "predict" it.

Real £ prize-per-winner amounts come from each draw's "prizes" field
(populated by scrape_lotto.py / scrape_euromillions.py at scrape time from
the official prize breakdown table — not backfilled for older draws).

Usage:
  python weekly_report.py --games lotto euromillions
"""

import argparse
import json
import os
import random
from datetime import datetime

from prize_table import LOTTO_TICKET_PRICE, EM_TICKET_PRICE

ROOT = os.path.join(os.path.dirname(__file__), '..')
LOTTO_FILE = os.path.join(ROOT, 'assets/data/lotto-results.json')
EM_FILE = os.path.join(ROOT, 'assets/data/euromillions-results.json')
LEDGER_FILE = os.path.join(ROOT, 'reports/ledger.json')

LINES_RANDOM = 10
LINES_WEIGHTED = 10

MODE_KEYS = ('random', 'weighted', 'topn')
MODE_LABELS = {'random': 'Random', 'weighted': 'Weighted', 'topn': 'Top N'}

EM_TIER_LABELS = {
    (5, 2): 'Match 5 + 2 Stars — JACKPOT',
    (5, 1): 'Match 5 + 1 Star',
    (5, 0): 'Match 5 + 0 Stars',
    (4, 2): 'Match 4 + 2 Stars',
    (4, 1): 'Match 4 + 1 Star',
    (3, 2): 'Match 3 + 2 Stars',
    (4, 0): 'Match 4 + 0 Stars',
    (2, 2): 'Match 2 + 2 Stars',
    (3, 1): 'Match 3 + 1 Star',
    (3, 0): 'Match 3 + 0 Stars',
    (1, 2): 'Match 1 + 2 Stars',
    (2, 1): 'Match 2 + 1 Star',
    (2, 0): 'Match 2 + 0 Stars',
}


def lotto_tier(matches, bonus_hit):
    if matches == 6:
        return '6', 'Match 6 — JACKPOT'
    if matches == 5 and bonus_hit:
        return '5+bonus', 'Match 5 + Bonus'
    if matches == 5:
        return '5', 'Match 5'
    if matches == 4:
        return '4', 'Match 4'
    if matches == 3:
        return '3', 'Match 3'
    if matches == 2:
        return '2', 'Match 2'
    return None, None


def build_freq(draws_of_numbers, max_n):
    freq = {i: 0 for i in range(1, max_n + 1)}
    for numbers in draws_of_numbers:
        for n in numbers:
            freq[n] += 1
    return freq


def top_n(freq, n):
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


def weighted_sample(freq, n):
    pool = list(freq.items())
    result = []
    for _ in range(n):
        total = sum(w for _, w in pool)
        if total <= 0:
            # No frequency signal left (e.g. brand-new game) — fall back to uniform pick.
            choice_idx = random.randrange(len(pool))
        else:
            r = random.random() * total
            choice_idx = 0
            for j, (_, w) in enumerate(pool):
                r -= w
                if r <= 0:
                    choice_idx = j
                    break
        result.append(pool.pop(choice_idx)[0])
    return result


def random_sample(max_n, n):
    result = set()
    while len(result) < n:
        result.add(random.randint(1, max_n))
    return list(result)


def load(path):
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def load_ledger():
    try:
        with open(LEDGER_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_ledger(ledger):
    os.makedirs(os.path.dirname(os.path.abspath(LEDGER_FILE)), exist_ok=True)
    with open(LEDGER_FILE, 'w') as f:
        json.dump(ledger, f, indent=2, sort_keys=True)


def year_bucket(ledger, game, mode, year):
    g = ledger.setdefault(game, {'last_reported_draw_date': None, 'modes': {}})
    m = g['modes'].setdefault(mode, {})
    return m.setdefault(year, {'draws': 0, 'lines': 0, 'cost': 0.0, 'winnings': 0.0})


def score_mode(lines, ledger, game, mode_key, year, score_line_fn, ticket_price):
    scored = []
    win_count = 0
    winnings = 0.0
    for line in lines:
        result = score_line_fn(line)
        scored.append(result)
        if result['tier']:
            win_count += 1
            winnings += result['amount']
    cost = len(lines) * ticket_price
    bucket = year_bucket(ledger, game, mode_key, year)
    bucket['draws'] += 1
    bucket['lines'] += len(lines)
    bucket['cost'] += cost
    bucket['winnings'] += winnings
    return {
        'lines': scored, 'win_count': win_count, 'total_lines': len(lines),
        'cost': cost, 'winnings': winnings, 'running': dict(bucket),
    }


def process_lotto_draw(target, history, ledger):
    target_main = sorted(int(n) for n in target['draw_result'].split(','))
    target_bonus = target['bonus_ball']
    prizes = target.get('prizes') or {}
    year = target['draw_date'][:4]

    history_numbers = [[int(n) for n in d['draw_result'].split(',')] for d in history]
    freq = build_freq(history_numbers, 59)
    top6 = top_n(freq, 6)

    def score_line(nums):
        matches = len(set(nums) & set(target_main))
        bonus_hit = target_bonus in nums and target_bonus not in target_main
        tier_key, tier_label = lotto_tier(matches, bonus_hit)
        amount = prizes.get(tier_key, 0.0) if tier_key else 0.0
        return {'numbers': sorted(nums), 'matches': matches, 'bonus_hit': bonus_hit,
                'tier': tier_label, 'amount': amount}

    mode_lines = {
        'random': [random_sample(59, 6) for _ in range(LINES_RANDOM)],
        'weighted': [weighted_sample(freq, 6) for _ in range(LINES_WEIGHTED)],
        'topn': [top6],
    }
    modes_out = {
        k: score_mode(lines, ledger, 'lotto', k, year, score_line, LOTTO_TICKET_PRICE)
        for k, lines in mode_lines.items()
    }

    ledger['lotto']['last_reported_draw_date'] = target['draw_date']

    return {
        'game': 'lotto', 'game_label': 'UK Lotto',
        'draw_date': target['draw_date'], 'draw_day': target['draw_day'],
        'winning_numbers': target_main, 'bonus_ball': target_bonus,
        'prize_data_available': bool(prizes),
        'modes': modes_out, 'year': year,
    }


def process_euromillions_draw(target, history, ledger):
    target_balls = sorted(target['b'])
    target_stars = sorted(target['s'])
    prizes = target.get('prizes') or {}
    year = target['date'][:4]

    freq_balls = build_freq([d['b'] for d in history], 50)
    freq_stars = build_freq([d['s'] for d in history], 12)
    top5_balls = top_n(freq_balls, 5)
    top2_stars = top_n(freq_stars, 2)

    def score_line(pair):
        balls, stars = pair
        ball_matches = len(set(balls) & set(target_balls))
        star_matches = len(set(stars) & set(target_stars))
        tier_label = EM_TIER_LABELS.get((ball_matches, star_matches))
        key = f"{ball_matches}-{star_matches}"
        amount = prizes.get(key, 0.0) if tier_label else 0.0
        return {'numbers': sorted(balls), 'stars': sorted(stars), 'matches': ball_matches,
                'star_matches': star_matches, 'tier': tier_label, 'amount': amount}

    mode_lines = {
        'random': [(random_sample(50, 5), random_sample(12, 2)) for _ in range(LINES_RANDOM)],
        'weighted': [(weighted_sample(freq_balls, 5), weighted_sample(freq_stars, 2)) for _ in range(LINES_WEIGHTED)],
        'topn': [(top5_balls, top2_stars)],
    }
    modes_out = {
        k: score_mode(lines, ledger, 'euromillions', k, year, score_line, EM_TICKET_PRICE)
        for k, lines in mode_lines.items()
    }

    ledger['euromillions']['last_reported_draw_date'] = target['date']

    return {
        'game': 'euromillions', 'game_label': 'EuroMillions',
        'draw_date': target['date'], 'draw_day': target['day'],
        'winning_numbers': target_balls, 'winning_stars': target_stars,
        'prize_data_available': bool(prizes),
        'modes': modes_out, 'year': year,
    }


def pending_targets(draws, date_field, last_reported_date):
    sorted_draws = sorted(draws, key=lambda d: d[date_field])
    if not sorted_draws:
        return []
    if last_reported_date is None:
        # First run of this feature: don't replay all of history, just
        # start tracking from the latest draw onward.
        return [(len(sorted_draws) - 1, sorted_draws)]
    return [(i, sorted_draws) for i, d in enumerate(sorted_draws) if d[date_field] > last_reported_date]


def fmt_money(x):
    sign = '-' if x < 0 else ''
    return f"{sign}£{abs(x):,.2f}"


def fmt_nums_text(numbers, winning_set):
    return ' '.join(f'*{n:02d}*' if n in winning_set else f'{n:02d}' for n in numbers)


def fmt_nums_html(numbers, winning_set):
    return ' '.join(f'<b>{n:02d}</b>' if n in winning_set else f'{n:02d}' for n in numbers)


def build_text(bundle):
    winning_main = set(bundle['winning_numbers'])
    is_em = bundle['game'] == 'euromillions'
    winning_stars = set(bundle.get('winning_stars', [])) if is_em else set()

    parts = [f"{bundle['game_label']} draw report — {bundle['draw_day']} {bundle['draw_date']}\n"]
    if is_em:
        win_str = (f"{' '.join(f'{n:02d}' for n in bundle['winning_numbers'])}  "
                    f"Stars: {' '.join(f'{n:02d}' for n in bundle['winning_stars'])}")
    else:
        win_str = (f"{' '.join(f'{n:02d}' for n in bundle['winning_numbers'])}  "
                    f"Bonus: {bundle['bonus_ball']:02d}")
    parts.append(f"Winning numbers: {win_str}")
    if not bundle['prize_data_available']:
        parts.append("(Real prize amounts weren't available for this draw — winnings shown as £0.)")
    parts.append('')

    for mode_key in MODE_KEYS:
        m = bundle['modes'][mode_key]
        parts.append('=' * 60)
        parts.append(f"{MODE_LABELS[mode_key]} — {m['win_count']}/{m['total_lines']} lines won "
                      f"({fmt_money(m['winnings'])} from {fmt_money(m['cost'])} staked)")
        for l in m['lines']:
            nums = fmt_nums_text(l['numbers'], winning_main)
            if is_em:
                stars = fmt_nums_text(l['stars'], winning_stars)
                row = f"  {nums}  Stars: {stars}"
            else:
                row = f"  {nums}"
            if l['tier']:
                row += f"  -> WIN: {l['tier']} ({fmt_money(l['amount'])})"
            parts.append(row)
        run = m['running']
        parts.append(f"  {bundle['year']} running total: {run['draws']} draws, {run['lines']} lines, "
                      f"staked {fmt_money(run['cost'])}, won {fmt_money(run['winnings'])}, "
                      f"net {fmt_money(run['winnings'] - run['cost'])}")
        parts.append('')
    return '\n'.join(parts)


def build_html(bundle):
    winning_main = set(bundle['winning_numbers'])
    is_em = bundle['game'] == 'euromillions'
    winning_stars = set(bundle.get('winning_stars', [])) if is_em else set()

    if is_em:
        winning_html = (f"{' '.join(f'{n:02d}' for n in bundle['winning_numbers'])} "
                         f"&nbsp;Stars: {' '.join(f'{n:02d}' for n in bundle['winning_stars'])}")
    else:
        winning_html = (f"{' '.join(f'{n:02d}' for n in bundle['winning_numbers'])} "
                         f"&nbsp;Bonus: {bundle['bonus_ball']:02d}")

    note = ''
    if not bundle['prize_data_available']:
        note = "<p><em>Real prize amounts weren't available for this draw — winnings shown as £0.</em></p>"

    sections = []
    for mode_key in MODE_KEYS:
        m = bundle['modes'][mode_key]
        rows = []
        for l in m['lines']:
            nums = fmt_nums_html(l['numbers'], winning_main)
            if is_em:
                nums += '&nbsp;&nbsp;Stars: ' + fmt_nums_html(l['stars'], winning_stars)
            win_cell = f"{l['tier']} ({fmt_money(l['amount'])})" if l['tier'] else '—'
            style = ' style="background:#e8f7e8"' if l['tier'] else ''
            rows.append(f"<tr{style}><td>{nums}</td><td>{win_cell}</td></tr>")

        run = m['running']
        net = run['winnings'] - run['cost']
        sections.append(f"""
        <h2>{MODE_LABELS[mode_key]}</h2>
        <p>{m['win_count']}/{m['total_lines']} lines won this draw
           (<strong>{fmt_money(m['winnings'])}</strong> from {fmt_money(m['cost'])} staked)</p>
        <table cellpadding="6" cellspacing="0" border="1" style="border-collapse:collapse;font-family:monospace">
          <tr><th>Numbers</th><th>Result</th></tr>
          {''.join(rows)}
        </table>
        <p style="font-size:0.9em;color:#555">
          {bundle['year']} running total: {run['draws']} draws, {run['lines']} lines,
          staked {fmt_money(run['cost'])}, won {fmt_money(run['winnings'])},
          net <strong>{fmt_money(net)}</strong>
        </p>
        """)

    return f"""
    <div style="font-family:sans-serif">
      <h1>{bundle['game_label']} draw report — {bundle['draw_day']} {bundle['draw_date']}</h1>
      <p><strong>Winning numbers:</strong> {winning_html}</p>
      {note}
      {''.join(sections)}
    </div>
    """


def make_bundle(report):
    date_display = datetime.strptime(report['draw_date'], '%Y-%m-%d').strftime('%d %b %Y')
    subject = f"{report['game_label']} draw report — {date_display}"
    return {
        'game': report['game'],
        'subject': subject,
        'text': build_text(report),
        'html': build_html(report),
    }


def report_pending(game, ledger):
    if game == 'lotto':
        draws = load(LOTTO_FILE)
        date_field = 'draw_date'
        process_fn = process_lotto_draw
    else:
        draws = load(EM_FILE)
        date_field = 'date'
        process_fn = process_euromillions_draw

    last_reported = ledger.get(game, {}).get('last_reported_draw_date')
    targets = pending_targets(draws, date_field, last_reported)

    bundles = []
    for idx, sorted_draws in targets:
        target = sorted_draws[idx]
        history = sorted_draws[:idx]
        if len(history) < 1:
            continue
        report = process_fn(target, history, ledger)
        bundles.append(make_bundle(report))
    return bundles


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--games', nargs='+', default=['lotto', 'euromillions'],
                         choices=['lotto', 'euromillions'])
    args = parser.parse_args()

    ledger = load_ledger()
    bundles = []
    if 'lotto' in args.games:
        bundles.extend(report_pending('lotto', ledger))
    if 'euromillions' in args.games:
        bundles.extend(report_pending('euromillions', ledger))

    if bundles:
        save_ledger(ledger)

    print(json.dumps({'reports': bundles}))


if __name__ == '__main__':
    main()
