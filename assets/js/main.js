'use strict';

const lotto_grid = document.getElementById("lotto");
const btn_spin = document.getElementById('btn_spin_lotto');
const btn_sync = document.getElementById('btn_sync');
const sync_label = document.getElementById('sync-label');

const GITHUB_FREQ_URL = 'https://raw.githubusercontent.com/leonharris/lottery/main/assets/data/frequency-data.json';

// 'random' | 'topn' | 'weighted'
let freq_mode = 'random';

// All frequency/topN data lives here; populated from FREQ_JSON (bundled) then optionally refreshed
let freq_data = null;

function applyFreqData(data) {
    freq_data = data;
    if (sync_label && data.generated) {
        const d = new Date(data.generated);
        sync_label.textContent = 'Data: ' + d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
    }
}

// Apply bundled data immediately (works with file:// protocol)
if (typeof FREQ_JSON !== 'undefined') applyFreqData(FREQ_JSON);

// Auto-check GitHub for newer data on page load
async function syncData(manual = false) {
    if (manual) {
        btn_sync.disabled = true;
        btn_sync.textContent = 'Syncing…';
    }
    try {
        const res = await fetch(GITHUB_FREQ_URL + '?t=' + Date.now());
        if (!res.ok) throw new Error(res.status);
        const data = await res.json();
        const isNewer = !freq_data || data.generated > freq_data.generated;
        if (isNewer) {
            applyFreqData(data);
            if (manual) btn_sync.textContent = '✓ Updated';
        } else {
            if (manual) btn_sync.textContent = '✓ Up to date';
        }
    } catch {
        if (manual) btn_sync.textContent = 'Sync failed';
    } finally {
        if (manual) {
            btn_sync.disabled = false;
            setTimeout(() => { btn_sync.textContent = 'Sync results'; }, 3000);
        }
    }
}

// Silent auto-check on load; manual button available for on-demand
syncData(false);

// --- frequency helpers ---

function weightedSample(freqMap, n) {
    const pool = Object.entries(freqMap).map(([k, w]) => [parseInt(k), w]);
    const result = [];
    for (let i = 0; i < n; i++) {
        const total = pool.reduce((s, [, w]) => s + w, 0);
        let r = Math.random() * total;
        for (let j = 0; j < pool.length; j++) {
            r -= pool[j][1];
            if (r <= 0) {
                result.push(pool[j][0]);
                pool.splice(j, 1);
                break;
            }
        }
    }
    return result;
}

function randomSample(max, n) {
    const arr = [];
    while (arr.length < n) {
        const r = Math.floor(Math.random() * max) + 1;
        if (!arr.includes(r)) arr.push(r);
    }
    return arr;
}

function pickNumbers(max, n, key) {
    if (freq_mode === 'topn' && freq_data) return freq_data[key].topN;
    if (freq_mode === 'weighted' && freq_data) return weightedSample(freq_data[key].freq, n);
    return randomSample(max, n);
}

// --- sort toggle ---

let sort_val = false;
document.getElementById("sort-toggle-switch").addEventListener('change', function () {
    sort_val = this.checked;
});

// --- draw type toggle ---

let draw_type = 'lotto';
document.getElementById("draw-type-toggle-switch").addEventListener('change', function () {
    reset_balls();
    draw_type = this.checked ? 'euromillions' : 'lotto';
    lotto_grid.setAttribute('data-draw-type', draw_type);
});

// --- mode selector ---

document.querySelectorAll('.mode-btn').forEach(btn => {
    btn.addEventListener('click', function () {
        document.querySelectorAll('.mode-btn').forEach(b => b.classList.remove('active'));
        this.classList.add('active');
        freq_mode = this.dataset.mode;
    });
});

// --- info popover ---

const info_btn = document.getElementById('info-btn');
const info_popover = document.getElementById('info-popover');

info_btn.addEventListener('click', function (e) {
    e.stopPropagation();
    const open = !info_popover.hidden;
    info_popover.hidden = open;
    info_btn.classList.toggle('active', !open);
});

document.addEventListener('click', function () {
    info_popover.hidden = true;
    info_btn.classList.remove('active');
});

// --- sync button ---

btn_sync.addEventListener('click', () => syncData(true));

// --- ball rendering ---

function reset_balls() {
    document.querySelectorAll('.ball').forEach(el => el.remove());
}

function renderBall(number, isStar) {
    const ball = document.createElement('div');
    const span = document.createElement('span');
    if (isStar) {
        ball.setAttribute('class', 'ball ball--star');
    } else {
        ball.setAttribute('class', 'ball');
        ball.setAttribute('data-range', 'range-' + Math.ceil((number / 10) + 0.01));
    }
    span.setAttribute('class', 'number');
    span.textContent = number;
    ball.append(span);
    lotto_grid.append(ball);
}

function generateNumbers(max, quantity, key, isStar) {
    let numbers = pickNumbers(max, quantity, key);
    if (sort_val) numbers = [...numbers].sort((a, b) => a - b);
    numbers.forEach(n => renderBall(n, isStar));
}

// --- spin ---

btn_spin.addEventListener("click", function () {
    reset_balls();
    if (draw_type === 'lotto') {
        generateNumbers(59, 6, 'lotto', false);
    } else {
        generateNumbers(50, 5, 'em_balls', false);
        generateNumbers(12, 2, 'em_stars', true);
    }
});
