// sensor-app emitter — Safari on iphone-xr. Sensors over WebSocket (JSON),
// video over WebSocket (JPEG). Streaming is a toggle; capture fps follows the
// phone camera's own frame rate (capped) and backs off under network pressure.

const CONFIG = {
  maxFps: 30,     // never send faster than this, even if the camera is quicker
  width: 640,     // JPEG width (height follows the camera aspect ratio)
  quality: 0.5,   // JPEG quality 0..1
  device: 'iphone-xr',
};

const $ = (id) => document.getElementById(id);
const wsBase = (location.protocol === 'https:' ? 'wss://' : 'ws://') + location.host;

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
function setToggle(text, variant) { // variant: 'primary' | 'destructive'
  const b = $('toggle');
  b.className = 'btn btn-lg btn-' + variant;
  b.textContent = text;
  b.disabled = false;
}

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

  // Adapt capture rate to the phone camera's actual frame rate.
  const st = stream.getVideoTracks()[0].getSettings();
  const camFps = Math.round(st.frameRate || CONFIG.maxFps);
  targetFps = Math.min(camFps, CONFIG.maxFps);
  $('m_cam').textContent = `${st.width || '?'}×${st.height || '?'}@${camFps}`;
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
    setToggle('Start streaming', 'primary');
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
  setBadge('idle', '');
  setToggle('Start streaming', 'primary');
  log('streaming stopped');
}

$('toggle').addEventListener('click', () => (running ? stop() : start()));

// ---------------- Live readouts ----------------
const fmt = (v, n = 1) => (typeof v === 'number' && isFinite(v)) ? v.toFixed(n) : '—';
setInterval(() => {
  $('m_fps').textContent = stats.frames - stats.lastFrames;
  stats.lastFrames = stats.frames;
  $('m_frames').textContent = stats.frames;
  $('m_pkts').textContent = stats.packets;
  const g = state.gyro || {}, a = state.accelG || {}, o = state.orient || {}, gp = state.gps;
  $('m_gyro').textContent = `${fmt(g.alpha)}, ${fmt(g.beta)}, ${fmt(g.gamma)}`;
  $('m_accel').textContent = `${fmt(a.x)}, ${fmt(a.y)}, ${fmt(a.z)}`;
  $('m_compass').textContent = fmt(o.compass, 0);
  $('m_gps').textContent = gp ? `${fmt(gp.lat, 5)}, ${fmt(gp.lon, 5)}` : '—';
}, 1000);
