#!/usr/bin/env python3
"""
Weekly draw report: generates 10 random + 10 weighted + 1 top-N line per
game, scores them against the most recently recorded real draw, and prints
a ready-to-send email as JSON: {"subject", "text", "html"}.

The frequency tables used for weighted/top-N generation are built from all
draws *before* the target draw, so the target draw's own result can't leak
into the numbers used to "predict" it.

Usage:
  python weekly_report.py --games lotto euromillions
"""

import argparse
import json
import os
import random
from datetime import datetime

ROOT = os.path.join(os.path.dirname(__file__), '..')
LOTTO_FILE = os.path.join(ROOT, 'assets/data/lotto-results.json')
EM_FILE = os.path.join(ROOT, 'assets/data/euromillions-results.json')

LINES_RANDOM = 10
LINES_WEIGHTED = 10

EM_WIN_TIERS = {
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
}


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


def generate_lines(mode_fn_random, mode_fn_weighted, topn_value):
    lines = []
    for _ in range(LINES_RANDOM):
        lines.append(('Random', mode_fn_random()))
    for _ in range(LINES_WEIGHTED):
        lines.append(('Weighted', mode_fn_weighted()))
    lines.append(('Top N', topn_value))
    return lines


def report_lotto():
    draws = sorted(load(LOTTO_FILE), key=lambda d: d['draw_date'])
    if len(draws) < 2:
        return None
    target, history = draws[-1], draws[:-1]

    target_main = [int(n) for n in target['draw_result'].split(',')]
    target_bonus = target['bonus_ball']

    history_numbers = [[int(n) for n in d['draw_result'].split(',')] for d in history]
    freq = build_freq(history_numbers, 59)
    top6 = top_n(freq, 6)

    lines = generate_lines(
        lambda: random_sample(59, 6),
        lambda: weighted_sample(freq, 6),
        top6,
    )

    scored = []
    for mode, nums in lines:
        matches = len(set(nums) & set(target_main))
        bonus_hit = target_bonus in nums and target_bonus not in target_main
        tier = None
        if matches == 6:
            tier = 'Match 6 — JACKPOT'
        elif matches == 5 and bonus_hit:
            tier = 'Match 5 + Bonus'
        elif matches == 5:
            tier = 'Match 5'
        elif matches == 4:
            tier = 'Match 4'
        elif matches == 3:
            tier = 'Match 3'
        elif matches == 2:
            tier = 'Match 2'
        scored.append({'mode': mode, 'numbers': sorted(nums), 'matches': matches, 'tier': tier})

    win_count = sum(1 for s in scored if s['tier'])
    return {
        'game': 'UK Lotto',
        'draw_date': target['draw_date'],
        'draw_day': target['draw_day'],
        'winning_numbers': sorted(target_main),
        'bonus_ball': target_bonus,
        'lines': scored,
        'win_count': win_count,
        'total_lines': len(scored),
        'win_pct': round(100 * win_count / len(scored), 1),
    }


def report_euromillions():
    draws = sorted(load(EM_FILE), key=lambda d: d['date'])
    if len(draws) < 2:
        return None
    target, history = draws[-1], draws[:-1]

    target_balls, target_stars = target['b'], target['s']

    freq_balls = build_freq([d['b'] for d in history], 50)
    freq_stars = build_freq([d['s'] for d in history], 12)
    top5_balls = top_n(freq_balls, 5)
    top2_stars = top_n(freq_stars, 2)

    lines = generate_lines(
        lambda: (random_sample(50, 5), random_sample(12, 2)),
        lambda: (weighted_sample(freq_balls, 5), weighted_sample(freq_stars, 2)),
        (top5_balls, top2_stars),
    )

    scored = []
    for mode, (balls, stars) in lines:
        ball_matches = len(set(balls) & set(target_balls))
        star_matches = len(set(stars) & set(target_stars))
        tier = EM_WIN_TIERS.get((ball_matches, star_matches))
        scored.append({
            'mode': mode,
            'numbers': sorted(balls),
            'stars': sorted(stars),
            'matches': ball_matches,
            'star_matches': star_matches,
            'tier': tier,
        })

    win_count = sum(1 for s in scored if s['tier'])
    return {
        'game': 'EuroMillions',
        'draw_date': target['date'],
        'draw_day': target['day'],
        'winning_numbers': sorted(target_balls),
        'winning_stars': sorted(target_stars),
        'lines': scored,
        'win_count': win_count,
        'total_lines': len(scored),
        'win_pct': round(100 * win_count / len(scored), 1),
    }


def format_line_text(game_key, line):
    nums = ' '.join(f'{n:02d}' for n in line['numbers'])
    if game_key == 'euromillions':
        stars = ' '.join(f'{n:02d}' for n in line['stars'])
        base = f"  [{line['mode']:<8}] {nums}  Stars: {stars}  -> {line['matches']} main + {line['star_matches']} star"
    else:
        base = f"  [{line['mode']:<8}] {nums}  -> {line['matches']} matches"
    if line['tier']:
        base += f"  *** WIN: {line['tier']} ***"
    return base


def build_text(reports):
    parts = [f"Weekly lottery draw report — {datetime.now().strftime('%A %d %B %Y')}\n"]
    for key, r in reports:
        if r is None:
            continue
        parts.append('=' * 60)
        parts.append(f"{r['game']} — {r['draw_day']} {r['draw_date']}")
        if key == 'euromillions':
            parts.append(f"Winning numbers: {' '.join(f'{n:02d}' for n in r['winning_numbers'])}  "
                          f"Stars: {' '.join(f'{n:02d}' for n in r['winning_stars'])}")
        else:
            parts.append(f"Winning numbers: {' '.join(f'{n:02d}' for n in r['winning_numbers'])}  "
                          f"Bonus: {r['bonus_ball']:02d}")
        parts.append(f"Win rate: {r['win_count']}/{r['total_lines']} lines won a prize ({r['win_pct']}%)\n")

        winners = [l for l in r['lines'] if l['tier']]
        if winners:
            parts.append('Winning lines:')
            for l in winners:
                parts.append(format_line_text(key, l))
        else:
            parts.append('No winning lines this draw.')

        parts.append('\nAll lines:')
        for l in r['lines']:
            parts.append(format_line_text(key, l))
        parts.append('')
    return '\n'.join(parts)


def build_html(reports):
    def esc(s):
        return str(s)

    sections = []
    for key, r in reports:
        if r is None:
            continue
        if key == 'euromillions':
            winning = (f"{' '.join(f'{n:02d}' for n in r['winning_numbers'])} "
                       f"&nbsp;Stars: {' '.join(f'{n:02d}' for n in r['winning_stars'])}")
        else:
            winning = (f"{' '.join(f'{n:02d}' for n in r['winning_numbers'])} "
                       f"&nbsp;Bonus: {r['bonus_ball']:02d}")

        rows = []
        for l in r['lines']:
            nums = ' '.join(f'{n:02d}' for n in l['numbers'])
            if key == 'euromillions':
                nums += '&nbsp;&nbsp;Stars: ' + ' '.join(f'{n:02d}' for n in l['stars'])
            win_cell = esc(l['tier']) if l['tier'] else '—'
            style = ' style="background:#e8f7e8;font-weight:600"' if l['tier'] else ''
            rows.append(f"<tr{style}><td>{esc(l['mode'])}</td><td>{nums}</td><td>{win_cell}</td></tr>")

        sections.append(f"""
        <h2>{esc(r['game'])} — {esc(r['draw_day'])} {esc(r['draw_date'])}</h2>
        <p><strong>Winning numbers:</strong> {winning}</p>
        <p><strong>Win rate:</strong> {r['win_count']}/{r['total_lines']} lines won a prize
           (<strong>{r['win_pct']}%</strong>)</p>
        <table cellpadding="6" cellspacing="0" border="1" style="border-collapse:collapse;font-family:monospace">
          <tr><th>Mode</th><th>Numbers</th><th>Result</th></tr>
          {''.join(rows)}
        </table>
        """)

    return f"""
    <div style="font-family:sans-serif">
      <h1>Weekly lottery draw report — {datetime.now().strftime('%A %d %B %Y')}</h1>
      {''.join(sections)}
    </div>
    """


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--games', nargs='+', default=['lotto', 'euromillions'],
                         choices=['lotto', 'euromillions'])
    args = parser.parse_args()

    reports = []
    if 'lotto' in args.games:
        reports.append(('lotto', report_lotto()))
    if 'euromillions' in args.games:
        reports.append(('euromillions', report_euromillions()))

    if all(r is None for _, r in reports):
        print(json.dumps({'subject': None, 'text': None, 'html': None,
                           'note': 'No draw data available for requested games.'}))
        return

    subject = 'Lottery draw report — ' + ', '.join(
        r['game'] for _, r in reports if r is not None
    ) + f" — {datetime.now().strftime('%d %b %Y')}"

    print(json.dumps({
        'subject': subject,
        'text': build_text(reports),
        'html': build_html(reports),
    }))


if __name__ == '__main__':
    main()
