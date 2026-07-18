// sensor-app dashboard — pure viewer. All compute happens on shawarma; this page
// only displays the server's live feed and plots the numbers it sends.

const $ = (id) => document.getElementById(id);
const wsBase = (location.protocol === 'https:' ? 'wss://' : 'ws://') + location.host;
const dpr = Math.max(1, window.devicePixelRatio || 1);
const fmt = (v, n = 1) => (typeof v === 'number' && isFinite(v)) ? v.toFixed(n) : '—';

$('server').textContent = location.hostname || 'shawarma';

// ---------------- live feed (display only) ----------------
function wireImg(id, path) {
  const img = $(id);
  const load = () => { img.src = path + '?t=' + Date.now(); };
  img.onerror = () => setTimeout(load, 1500);   // retry if the server restarts
  load();
}
wireImg('feed', '/stream/cv.mjpeg');

// ---------------- tiny dependency-free strip chart ----------------
class Strip {
  constructor(canvas, series) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this.series = series;                 // [{color}]
    this.N = 240;
    this.data = series.map(() => []);
    this.resize();
  }
  resize() {
    const c = this.canvas;
    c.width = Math.max(1, Math.floor(c.clientWidth * dpr));
    c.height = Math.max(1, Math.floor(c.clientHeight * dpr));
  }
  push(vals) {
    for (let i = 0; i < this.series.length; i++) {
      const v = vals[i], a = this.data[i];
      a.push((typeof v === 'number' && isFinite(v)) ? v : 0);
      if (a.length > this.N) a.shift();
    }
  }
  draw() {
    const { ctx, canvas: c } = this, W = c.width, H = c.height;
    ctx.clearRect(0, 0, W, H);

    let mn = Infinity, mx = -Infinity;
    for (const a of this.data) for (const v of a) { if (v < mn) mn = v; if (v > mx) mx = v; }
    if (!isFinite(mn)) { mn = -1; mx = 1; }
    if (mn === mx) { mn -= 1; mx += 1; }
    const pad = (mx - mn) * 0.15; mn -= pad; mx += pad;
    const yOf = (v) => H - ((v - mn) / (mx - mn)) * H;

    if (mn < 0 && mx > 0) {
      ctx.strokeStyle = 'rgba(255,255,255,0.08)'; ctx.lineWidth = 1;
      ctx.beginPath(); ctx.moveTo(0, yOf(0)); ctx.lineTo(W, yOf(0)); ctx.stroke();
    }
    const step = W / (this.N - 1);
    for (let i = 0; i < this.series.length; i++) {
      const a = this.data[i];
      if (a.length < 2) continue;
      const offset = W - (a.length - 1) * step;
      ctx.strokeStyle = this.series[i].color;
      ctx.lineWidth = 1.5 * dpr;
      ctx.lineJoin = 'round';
      ctx.beginPath();
      for (let j = 0; j < a.length; j++) {
        const x = offset + j * step, y = yOf(a[j]);
        j ? ctx.lineTo(x, y) : ctx.moveTo(x, y);
      }
      ctx.stroke();
    }
  }
}

const charts = {
  gyro: new Strip($('c_gyro'), [{ color: '#22d3ee' }, { color: '#a78bfa' }, { color: '#f472b6' }]),
  accel: new Strip($('c_accel'), [{ color: '#22d3ee' }, { color: '#a78bfa' }, { color: '#f472b6' }]),
};
window.addEventListener('resize', () => { for (const k in charts) charts[k].resize(); });

// ---------------- websockets ----------------
function setDot(id, on) { $(id).className = 'dot' + (on ? ' on' : ''); }

function connect(path, onmsg, dot) {
  const open = () => {
    const ws = new WebSocket(wsBase + path);
    ws.onopen = () => setDot(dot, true);
    ws.onmessage = (e) => { try { onmsg(JSON.parse(e.data)); } catch {} };
    ws.onclose = () => { setDot(dot, false); setTimeout(open, 1200); };
    ws.onerror = () => {};
  };
  open();
}

connect('/ws/stream/sensors', (s) => {
  const g = s.gyro || {}, a = s.accelG || {}, o = s.orient || {}, gp = s.gps;
  charts.gyro.push([g.alpha, g.beta, g.gamma]);
  charts.accel.push([a.x, a.y, a.z]);
  $('r_compass').textContent = fmt(o.compass, 0);
  $('r_orient').textContent = `${fmt(o.alpha)}, ${fmt(o.beta)}, ${fmt(o.gamma)}`;
  $('r_gps').textContent = gp ? `${fmt(gp.lat, 4)}, ${fmt(gp.lon, 4)}` : '—';
}, 'dot_sensors');

connect('/ws/stream/cv', (c) => {
  $('m_brightness').textContent = fmt(c.brightness, 1);
  $('m_motion').textContent = fmt(c.motion, 2);
  $('m_res').textContent = (c.width && c.height) ? `${c.width}×${c.height}` : '—';
}, 'dot_cv');

// ---------------- render loop ----------------
function loop() { for (const k in charts) charts[k].draw(); requestAnimationFrame(loop); }
requestAnimationFrame(loop);
