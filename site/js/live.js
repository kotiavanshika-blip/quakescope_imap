// Live graphs: asks Prometheus for numbers every 5 seconds and draws them.
const PROM = '/prom/api/v1';
const WINDOW = '30s';   // "rate over the last 30 seconds"

const Q = {
  rate: `sum(rate(http_requests_total[${WINDOW}]))`,
  err: `(sum(rate(http_requests_total{status=~"5.."}[${WINDOW}])) or vector(0)) / sum(rate(http_requests_total[${WINDOW}]))`,
  pct: p => `histogram_quantile(${p}, sum by (le) (rate(http_request_duration_seconds_bucket[${WINDOW}])))`,
};

const $ = id => document.getElementById(id);
const num = v => (v == null || isNaN(v)) ? null : v;

async function instant(query) {
  try {
    const r = await fetch(`${PROM}/query?query=${encodeURIComponent(query)}`);
    const res = (await r.json()).data.result;
    return res.length ? num(parseFloat(res[0].value[1])) : null;
  } catch (e) { return null; }
}

// Returns [[time, value], ...] for the last 10 minutes.
async function history(query) {
  try {
    const end = Math.floor(Date.now() / 1000), start = end - 600;
    const r = await fetch(`${PROM}/query_range?query=${encodeURIComponent(query)}&start=${start}&end=${end}&step=5`);
    const res = (await r.json()).data.result;
    return res.length ? res[0].values.map(([t, v]) => [t, num(parseFloat(v))]) : [];
  } catch (e) { return []; }
}

const fmtSeconds = v => v == null ? '–' : v < 1 ? Math.round(v * 1000) + ' ms' : v.toFixed(2) + ' s';
const fmtPct = v => v == null ? '–' : (v * 100).toFixed(1) + '%';
const clock = t => new Date(t * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });

Chart.defaults.font.family = 'Inter, system-ui, sans-serif';
Chart.defaults.font.size = 12;
Chart.defaults.color = '#9aa6bf';

function makeChart(canvasId, lines, tick, extra = {}) {
  return new Chart($(canvasId), {
    type: 'line',
    data: { labels: [], datasets: lines.map(([label, color, fill]) => ({
      label, borderColor: color, backgroundColor: fill || color, fill: !!fill, data: [], borderWidth: 2.5, pointRadius: 0, tension: 0.25,
    })) },
    options: {
      animation: false, maintainAspectRatio: false, responsive: true,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { display: lines.length > 1, position: 'bottom', labels: { usePointStyle: true, boxWidth: 8, padding: 16 } },
        tooltip: { backgroundColor: '#05070f', borderColor: 'rgba(255,255,255,.16)', borderWidth: 1, padding: 10, titleColor: '#eef2fb', bodyColor: '#c9d3ea' },
      },
      scales: {
        x: { ticks: { maxTicksLimit: 6, maxRotation: 0 }, grid: { color: 'rgba(255,255,255,.05)' }, border: { display: false } },
        y: Object.assign({ beginAtZero: true, grid: { color: 'rgba(255,255,255,.07)' }, border: { display: false }, ticks: { callback: tick } }, extra),
      },
    },
  });
}

const cRate = makeChart('cRate', [['requests per second', '#5b8cff', 'rgba(91,140,255,0.16)']], v => v.toFixed(1));
const cLat = makeChart('cLat', [['p50', '#3ddc97'], ['p95', '#ffb547'], ['p99', '#ff5d73']], fmtSeconds);
const cErr = makeChart('cErr', [['errors', '#ff5d73', 'rgba(255,93,115,0.16)']], v => v.toFixed(0) + '%', { suggestedMax: 5, ticks: { stepSize: 1, callback: v => v.toFixed(0) + '%' } });

function draw(chart, seriesList, scale = 1) {
  const base = seriesList[0];
  chart.data.labels = base.map(([t]) => clock(t));
  seriesList.forEach((s, i) => { chart.data.datasets[i].data = s.map(([, v]) => v == null ? null : v * scale); });
  chart.update();
}

async function refresh() {
  const [rate, err, p95] = await Promise.all([instant(Q.rate), instant(Q.err), instant(Q.pct(0.95))]);
  $('nRate').textContent = rate == null ? '–' : rate.toFixed(1);
  $('nErr').textContent = fmtPct(err);
  $('nP95').textContent = fmtSeconds(p95);
  $('offline').hidden = rate != null;
  const pill = $('pill');
  pill.className = 'status-pill ' + (rate != null ? 'live' : 'off');
  $('pillText').textContent = rate != null ? 'Live · updated ' + new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : 'Waiting for data';
  $('sErr').classList.toggle('bad', err != null && err > 0.05);
  $('sP95').classList.toggle('bad', p95 != null && p95 > 1);

  const [h1, h50, h95, h99, hErr] = await Promise.all([
    history(Q.rate), history(Q.pct(0.5)), history(Q.pct(0.95)), history(Q.pct(0.99)), history(Q.err),
  ]);
  if (h1.length) draw(cRate, [h1]);
  if (h50.length) draw(cLat, [h50, h95, h99]);
  if (hErr.length) draw(cErr, [hErr], 100);
}
refresh();
setInterval(refresh, 5000);

// ---- Break it on purpose: send test traffic for 30 seconds
const sleep = ms => new Promise(r => setTimeout(r, ms));
let running = false;

function runTest(label, url, workers, pause) {
  if (running) return;
  running = true;
  $('bErr').disabled = $('bSlow').disabled = true;
  const end = Date.now() + 30000;
  $('prog').classList.add('on');
  for (let i = 0; i < workers; i++) {
    (async () => {
      while (Date.now() < end) {
        try { await fetch(url, { cache: 'no-store' }); } catch (e) { /* ignore */ }
        await sleep(pause);
      }
    })();
  }
  const timer = setInterval(() => {
    const left = Math.ceil((end - Date.now()) / 1000);
    $('prog').firstElementChild.style.width = Math.min(100, (30 - left) / 30 * 100) + '%';
    if (left <= 0) {
      clearInterval(timer);
      running = false;
      $('bErr').disabled = $('bSlow').disabled = false;
      $('status').textContent = 'Finished. Watch the graphs return to normal.';
      $('prog').classList.remove('on'); $('prog').firstElementChild.style.width = '0';
    } else {
      $('status').textContent = `${label}: ${left} seconds left. Watch the graphs above.`;
    }
  }, 500);
}

$('bErr').addEventListener('click', () => runTest('Sending errors', '/api/test/error?rate=0.9', 2, 150));
$('bSlow').addEventListener('click', () => runTest('Sending slow requests', '/api/test/slow?delay=2', 4, 50));
