// RidewMe emitter — Safari on iphone-xr. Sensors over WebSocket (JSON), video
// over WebSocket (JPEG). Streaming is a toggle; capture fps follows the phone
// camera's own frame rate (capped) and backs off under network pressure. The
// accel/gyro graphs plot the phone's OWN sensor data locally (no server trip).

const CONFIG = {
  maxFps: 30,     // never send faster than this, even if the camera is quicker
  width: 640,     // JPEG width (height follows the camera aspect ratio)
  quality: 0.5,   // JPEG quality 0..1
  device: 'iphone-xr',
};

const $ = (id) => document.getElementById(id);
const wsBase = (location.protocol === 'https:' ? 'wss://' : 'ws://') + location.host;
const dpr = Math.max(1, window.devicePixelRatio || 1);

const state = { accel: null, accelG: null, gyro: null, orient: null, gps: null, interval: null };
const stats = { frames: 0, packets: 0, lastFrames: 0 };

let sensorWS = null, videoWS = null;
let stream = null, wakeLock = null, running = false;
let captureTimer = null, watchId = null, targetFps = 0;

function log(msg) {
  const el = $('log');
  el.textContent = `[${new Date().toLocaleTimeString()}] ${msg}\n` + el.textContent;
}
function setBadge(text, kind) { // kind: '' | 'live' | 'off'
  $('badge').className = 'badge' + (kind ? ' badge-' + kind : '');
  $('badgeText').textContent = text;
}
function setToggle(text, variant) { // variant: 'success' | 'destructive'
  const b = $('toggle');
  b.className = 'btn btn-lg btn-' + variant;
  b.textContent = text;
  b.disabled = false;
}

// ---------------- live strip charts (local sensor data) ----------------
class Strip {
  constructor(canvas, colors) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this.colors = colors;
    this.N = 220;
    this.data = colors.map(() => []);
    this.resize();
  }
  resize() {
    const c = this.canvas;
    c.width = Math.max(1, Math.floor(c.clientWidth * dpr));
    c.height = Math.max(1, Math.floor(c.clientHeight * dpr));
  }
  push(vals) {
    for (let i = 0; i < this.colors.length; i++) {
      const v = vals[i], a = this.data[i];
      a.push((typeof v === 'number' && isFinite(v)) ? v : 0);
      if (a.length > this.N) a.shift();
    }
  }
  clear() { this.data = this.colors.map(() => []); }
  draw() {
    const { ctx, canvas: c } = this, W = c.width, H = c.height;
    ctx.clearRect(0, 0, W, H);
    let mn = Infinity, mx = -Infinity;
    for (const a of this.data) for (const v of a) { if (v < mn) mn = v; if (v > mx) mx = v; }
    if (!isFinite(mn)) { mn = -1; mx = 1; }
    if (mn === mx) { mn -= 1; mx += 1; }
    const pad = (mx - mn) * 0.15; mn -= pad; mx += pad;
    const yOf = (v) => H - ((v - mn) / (mx - mn)) * H;

    ctx.shadowBlur = 0;
    if (mn < 0 && mx > 0) {
      ctx.strokeStyle = 'rgba(255,255,255,0.06)'; ctx.lineWidth = 1;
      ctx.beginPath(); ctx.moveTo(0, yOf(0)); ctx.lineTo(W, yOf(0)); ctx.stroke();
    }
    const step = W / (this.N - 1);
    for (let i = 0; i < this.colors.length; i++) {
      const a = this.data[i];
      if (a.length < 2) continue;
      const offset = W - (a.length - 1) * step;
      ctx.strokeStyle = this.colors[i];
      ctx.lineWidth = 1.25 * dpr;
      ctx.lineJoin = 'round';
      ctx.shadowColor = this.colors[i];
      ctx.shadowBlur = 5 * dpr;
      ctx.beginPath();
      for (let j = 0; j < a.length; j++) {
        const x = offset + j * step, y = yOf(a[j]);
        j ? ctx.lineTo(x, y) : ctx.moveTo(x, y);
      }
      ctx.stroke();
    }
  }
}
const AXES = ['#22d3ee', '#a78bfa', '#f472b6'];
const charts = { accel: new Strip($('c_accel'), AXES), gyro: new Strip($('c_gyro'), AXES) };
window.addEventListener('resize', () => { for (const k in charts) charts[k].resize(); });
function drawLoop() { for (const k in charts) charts[k].draw(); requestAnimationFrame(drawLoop); }
requestAnimationFrame(drawLoop);

// ---------------- WebSockets ----------------
function connectWS(path) {
  const ws = new WebSocket(wsBase + path);
  ws.onopen = () => log('connected ' + path);
  ws.onerror = () => log('error ' + path);
  ws.onclose = () => {
    if (!running) return;
    log('closed ' + path + ' — reconnecting…');
    setTimeout(() => {
      if (!running) return;
      if (path === '/ws/sensors') sensorWS = connectWS(path);
      if (path === '/ws/video') videoWS = connectWS(path);
    }, 1000);
  };
  return ws;
}

// ---------------- Sensors ----------------
function sendSensor() {
  if (!sensorWS || sensorWS.readyState !== WebSocket.OPEN) return;
  sensorWS.send(JSON.stringify({
    device: CONFIG.device, t: Date.now(), mono: performance.now(), interval: state.interval,
    accel: state.accel, accelG: state.accelG, gyro: state.gyro, orient: state.orient, gps: state.gps,
  }));
  stats.packets++;
}
function onMotion(e) {
  const a = e.acceleration || {}, ag = e.accelerationIncludingGravity || {}, r = e.rotationRate || {};
  state.accel = { x: a.x, y: a.y, z: a.z };
  state.accelG = { x: ag.x, y: ag.y, z: ag.z };
  state.gyro = { alpha: r.alpha, beta: r.beta, gamma: r.gamma };
  state.interval = e.interval;
  charts.accel.push([ag.x, ag.y, ag.z]);        // plot locally, ~60 Hz
  charts.gyro.push([r.alpha, r.beta, r.gamma]);
  sendSensor();
}
function onOrient(e) {
  state.orient = { alpha: e.alpha, beta: e.beta, gamma: e.gamma, compass: (e.webkitCompassHeading ?? null) };
}
function onGeo(pos) {
  const c = pos.coords;
  state.gps = { lat: c.latitude, lon: c.longitude, alt: c.altitude, acc: c.accuracy, speed: c.speed, heading: c.heading };
}

async function requestPermissions() {
  if (typeof DeviceMotionEvent !== 'undefined' && typeof DeviceMotionEvent.requestPermission === 'function') {
    try { await DeviceMotionEvent.requestPermission(); } catch { log('motion permission denied'); }
  }
  if (typeof DeviceOrientationEvent !== 'undefined' && typeof DeviceOrientationEvent.requestPermission === 'function') {
    try { await DeviceOrientationEvent.requestPermission(); } catch { log('orientation permission denied'); }
  }
}
function startSensors() {
  window.addEventListener('devicemotion', onMotion);
  window.addEventListener('deviceorientation', onOrient);
  if ('geolocation' in navigator) {
    watchId = navigator.geolocation.watchPosition(onGeo, (e) => log('gps: ' + e.message),
      { enableHighAccuracy: true, maximumAge: 0, timeout: 15000 });
  }
}
function stopSensors() {
  window.removeEventListener('devicemotion', onMotion);
  window.removeEventListener('deviceorientation', onOrient);
  if (watchId !== null) { navigator.geolocation.clearWatch(watchId); watchId = null; }
}

// ---------------- Video ----------------
async function startVideo() {
  const video = $('cam');
  stream = await navigator.mediaDevices.getUserMedia({
    video: { facingMode: { ideal: 'environment' }, width: { ideal: 1280 }, height: { ideal: 720 }, frameRate: { ideal: CONFIG.maxFps } },
    audio: false,
  });
  video.srcObject = stream;
  await video.play();

  const st = stream.getVideoTracks()[0].getSettings();
  const camFps = Math.round(st.frameRate || CONFIG.maxFps);
  targetFps = Math.min(camFps, CONFIG.maxFps);
  $('m_cam').textContent = `${st.width || '?'}×${st.height || '?'} @${camFps}`;
  log(`camera ${st.width}×${st.height} @${camFps} → sending up to ${targetFps} fps`);

  const canvas = $('work');
  const ctx = canvas.getContext('2d');
  captureTimer = setInterval(() => {
    if (!videoWS || videoWS.readyState !== WebSocket.OPEN) return;
    if (videoWS.bufferedAmount > 1_000_000) return;   // network can't keep up: skip, stay live
    const vw = video.videoWidth, vh = video.videoHeight;
    if (!vw) return;
    const tw = CONFIG.width, th = Math.round(vh * tw / vw);
    if (canvas.width !== tw) { canvas.width = tw; canvas.height = th; }
    ctx.drawImage(video, 0, 0, tw, th);
    canvas.toBlob((blob) => {
      if (blob && videoWS && videoWS.readyState === WebSocket.OPEN) { videoWS.send(blob); stats.frames++; }
    }, 'image/jpeg', CONFIG.quality);
  }, Math.round(1000 / targetFps));
}

// ---------------- Keep screen awake ----------------
async function keepAwake() {
  try {
    if ('wakeLock' in navigator) {
      wakeLock = await navigator.wakeLock.request('screen');
      document.addEventListener('visibilitychange', async () => {
        if (document.visibilityState === 'visible' && running) {
          try { wakeLock = await navigator.wakeLock.request('screen'); } catch {}
        }
      });
    }
  } catch { log('wakeLock unavailable — keep the screen on manually'); }
}

// ---------------- Start / Stop ----------------
async function start() {
  if (running) return;

  // iOS exposes camera + motion sensors ONLY on a secure (https) origin.
  if (!window.isSecureContext || !navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    const good = 'https://' + location.hostname + '/emit';
    setBadge('https required', 'off');
    log('Camera + sensors are BLOCKED because this page is not a secure (https) origin.');
    log('You are on:  ' + location.protocol + '//' + location.host);
    log('Open this instead:  ' + good);
    return;
  }

  $('toggle').disabled = true;
  setBadge('starting…', '');
  charts.accel.clear(); charts.gyro.clear();
  try {
    await requestPermissions();
    sensorWS = connectWS('/ws/sensors');
    videoWS = connectWS('/ws/video');
    running = true;
    startSensors();
    await startVideo();
    await keepAwake();
    setBadge('live', 'live');
    setToggle('Stop streaming', 'destructive');
    log('streaming started');
  } catch (e) {
    running = false;
    setBadge('start failed', 'off');
    setToggle('Start streaming', 'success');
    log('start failed: ' + e.message);
  }
}

function stop() {
  running = false;
  if (captureTimer) { clearInterval(captureTimer); captureTimer = null; }
  stopSensors();
  if (stream) { stream.getTracks().forEach((t) => t.stop()); stream = null; }
  const v = $('cam'); if (v) v.srcObject = null;
  for (const ws of [sensorWS, videoWS]) { try { ws && ws.close(); } catch {} }
  sensorWS = videoWS = null;
  if (wakeLock) { try { wakeLock.release(); } catch {} wakeLock = null; }
  $('m_cam').textContent = '—';
  setBadge('idle', '');
  setToggle('Start streaming', 'success');
  log('streaming stopped');
}

$('toggle').addEventListener('click', () => (running ? stop() : start()));

// ---------------- Live readouts (1 Hz) ----------------
const fmt = (v, n = 1) => (typeof v === 'number' && isFinite(v)) ? v.toFixed(n) : '—';
setInterval(() => {
  $('m_fps').textContent = stats.frames - stats.lastFrames;
  stats.lastFrames = stats.frames;
  $('m_pkts').textContent = stats.packets;
  const gp = state.gps;
  $('m_gps').textContent = gp ? `${fmt(gp.lat, 4)}, ${fmt(gp.lon, 4)}` : '—';
}, 1000);
