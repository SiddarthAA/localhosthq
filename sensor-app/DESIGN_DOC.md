# RidewMe — Design System

The visual language behind the `/emit` emitter, documented so you can recreate
the same look on any other view (e.g. a processed-data dashboard) or port it to
another stack. **This is the design system only — not the page layout.**

Aesthetic in one line: **sharp, thin, futuristic HUD** — near-black cool
background, frosted-glass panels with hairline cyan-tinted borders, corner
"ticks", thin wide-tracked uppercase type, cyan tech accent with green/red action
semantics, and subtle neon glows.

---

## 1. Stack — what's actually used

| Concern | Choice | Notes |
|---|---|---|
| Markup | Plain **HTML5** | no framework |
| Styling | **Hand-written CSS** with custom properties | **no Tailwind, no CSS framework, no preprocessor** |
| Components | **shadcn/ui-*inspired*** (naming + HSL token convention) | **not** the shadcn npm package; it's React — this is plain CSS |
| Logic / charts | **Vanilla JS** (ES2020), **`<canvas>` 2D** | **no charting library** (Chart.js, D3, etc.) |
| Build step | **None** | files served statically; nothing to compile |
| Fonts | **System font stacks** | no web-font download |
| Icons | none (Unicode glyphs like `●`) | keep dependency-free |

> Reproducibility principle: **zero dependencies, zero build.** One CSS file
> (`ui.css`) holds the whole system; pages just link it and use the classes.

---

## 2. Design tokens

All colors are stored as **HSL channel triplets** (`H S% L%`) in `:root`, then
consumed with `hsl(var(--token))`. This is the shadcn convention and is the key
trick that makes every color alpha-composable: `hsl(var(--primary) / .3)`.

```css
:root {
  --background: 220 16% 4%;          /* near-black, cool */
  --foreground: 0 0% 96%;            /* primary text */
  --card: 210 16% 7%;                /* panel base (used translucent) */
  --border: 195 24% 20%;             /* faint cyan-tinted hairline */
  --muted: 210 10% 58%;              /* secondary text / labels */

  --primary: 186 100% 52%;           /* CYAN — tech accent, HUD ticks, focus, glow */
  --primary-foreground: 200 100% 6%;

  --success: 152 68% 45%;            /* GREEN — start / live / positive */
  --success-foreground: 150 100% 5%;

  --destructive: 0 82% 62%;          /* RED — stop / error */
  --destructive-foreground: 0 0% 98%;

  --ring: 186 100% 52%;              /* focus ring (= primary) */
  --radius: 3px;                     /* global corner radius (sharp) */
}
```

**Chart series palette** (used directly, not as tokens):
`#22d3ee` (cyan) · `#a78bfa` (violet) · `#f472b6` (pink).

### Color roles

| Token | Meaning | Where it appears |
|---|---|---|
| `--background` | app canvas | `body` |
| `--card` | elevated surface | panels (translucent, blurred) |
| `--border` | hairline separation | all panel/badge borders |
| `--foreground` / `--muted` | text high / low emphasis | values / labels |
| `--primary` (cyan) | "tech" accent, never an action | HUD ticks, focus ring, glows, brand accent, chart line 1 |
| `--success` (green) | go / live / start | primary CTA, live badge, status dot |
| `--destructive` (red) | stop / error | stop CTA, error badge |

Rule of thumb: **cyan = ambient/tech, green = go, red = stop.** Don't use cyan for
a clickable action or the semantics blur.

---

## 3. Typography

```css
/* sans (default) */
font-family: ui-sans-serif, -apple-system, system-ui, "Segoe UI", Roboto, sans-serif;

/* mono — all numbers */
.mono { font-family: ui-monospace, "SF Mono", Menlo, monospace;
        font-variant-numeric: tabular-nums; letter-spacing: .5px; }
```

The "thin/futuristic" feel comes from **type treatment, not a thin font**:

| Element | Size | Weight | Tracking | Case |
|---|---|---|---|---|
| Micro-label (`.k`) | 9–10px | 600 | 1.2–3.5px | UPPERCASE |
| Value (`.v`) | 16px | 500 | mono | — |
| Button | 12.5px | 600 | 2px | UPPERCASE |
| Badge | 10px | 600 | 1.5px | UPPERCASE |
| Panel heading | 10px | 600 | 1.5px | UPPERCASE |

Principles: **small sizes + wide letter-spacing + uppercase micro-labels +
tabular mono numerics.** Numbers always in `.mono` so they don't jitter as they
update.

---

## 4. Surfaces

### Card (frosted glass + hairline)

```css
.card {
  position: relative;
  background: hsl(var(--card) / .5);          /* translucent */
  -webkit-backdrop-filter: blur(9px);
  backdrop-filter: blur(9px);                  /* frosted glass over the grid bg */
  border: 1px solid hsl(var(--border));        /* hairline */
  border-radius: var(--radius);                /* 3px = sharp */
}
```

### HUD corner ticks

Diagonal cyan L-brackets on the top-left and bottom-right of important panels.
Add class `hud` to any `.card`. Pure pseudo-elements, no markup:

```css
.hud::before, .hud::after {
  content: ""; position: absolute; width: 11px; height: 11px;
  pointer-events: none; z-index: 2;
  border: 0 solid hsl(var(--primary) / .85);
}
.hud::before { top: -1px; left: -1px;  border-top-width: 1px;    border-left-width: 1px; }
.hud::after  { bottom: -1px; right: -1px; border-bottom-width: 1px; border-right-width: 1px; }
```

> Use `.hud` on large panels only (media, chart panels). Leave small pills plain
> — the contrast is the hierarchy.

---

## 5. Components

### Button

```css
.btn {
  --h: 48px;
  display: inline-flex; align-items: center; justify-content: center; gap: 8px;
  height: var(--h); padding: 0 18px;
  border: 1px solid transparent; border-radius: var(--radius);
  font-size: 12.5px; font-weight: 600; letter-spacing: 2px; text-transform: uppercase;
  cursor: pointer; user-select: none;
  transition: transform .04s ease, background .15s ease, box-shadow .15s ease, opacity .15s ease;
}
.btn:active { transform: translateY(1px); }
.btn:focus-visible { outline: none;
  box-shadow: 0 0 0 1px hsl(var(--background)), 0 0 0 3px hsl(var(--ring) / .6); }
.btn:disabled { opacity: .55; cursor: not-allowed; }
.btn-lg { --h: 50px; }

/* variants — solid fill + outer glow + inset top highlight */
.btn-success     { background: hsl(var(--success) / .95); color: hsl(var(--success-foreground));
  box-shadow: 0 0 24px hsl(var(--success) / .30), inset 0 1px 0 hsl(0 0% 100% / .18); }
.btn-destructive { background: hsl(var(--destructive) / .95); color: hsl(var(--destructive-foreground));
  box-shadow: 0 0 24px hsl(var(--destructive) / .30), inset 0 1px 0 hsl(0 0% 100% / .18); }
.btn-primary     { background: hsl(var(--primary)); color: hsl(var(--primary-foreground));
  box-shadow: 0 0 24px hsl(var(--primary) / .25); }
.btn-outline     { background: transparent; border-color: hsl(var(--border)); color: hsl(var(--foreground)); }
.btn-outline:hover { border-color: hsl(var(--primary) / .6); color: hsl(var(--primary)); }
```

The two signatures that make it "fancy": the **outer color glow** (`0 0 24px …/.30`)
and the **1px inset top highlight** (fakes a lit top edge).

### Badge + status dot

```css
.badge {
  display: inline-flex; align-items: center; gap: 7px;
  height: 22px; padding: 0 9px; border-radius: 2px;                 /* sharp, not a pill */
  border: 1px solid hsl(var(--border)); background: hsl(var(--foreground) / .02);
  font-size: 10px; font-weight: 600; letter-spacing: 1.5px; text-transform: uppercase;
  color: hsl(var(--muted));
}
.badge-live { color: hsl(var(--success)); border-color: hsl(var(--success) / .5); background: hsl(var(--success) / .08); }
.badge-off  { color: hsl(var(--destructive)); border-color: hsl(var(--destructive) / .5); background: hsl(var(--destructive) / .08); }

.dot { width: 6px; height: 6px; border-radius: 50%; background: hsl(var(--muted) / .5); flex: none; }
.dot.on { background: hsl(var(--success)); box-shadow: 0 0 8px hsl(var(--success)); }

@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: .35; } }
.badge-live .dot { background: hsl(var(--success)); box-shadow: 0 0 7px hsl(var(--success)); animation: pulse 1.4s ease-in-out infinite; }
.badge-off  .dot { background: hsl(var(--destructive)); box-shadow: 0 0 7px hsl(var(--destructive)); }
```

Pattern: `<span class="badge"><i class="dot"></i><span>LABEL</span></span>`, and
toggle `badge-live` / `badge-off` in JS to recolor state.

### Stat block (label + value)

```css
.stat { padding: 10px 12px; }
.stat .k { font-size: 9px; text-transform: uppercase; letter-spacing: 1.2px; color: hsl(var(--muted)); font-weight: 600; }
.stat .v { font-size: 16px; margin-top: 5px; color: hsl(var(--foreground)); font-weight: 500; }
```

Compose with a card: `<div class="stat card"><div class="k">FPS</div><div class="v mono">30</div></div>`.

---

## 6. Background (grid + glow)

A fixed, non-interactive layer behind everything — a top-centered radial glow plus
a faint 40px tech grid:

```css
body::before {
  content: ""; position: fixed; inset: 0; z-index: 0; pointer-events: none;
  background:
    radial-gradient(820px 440px at 50% -10%, hsl(var(--primary) / .09), transparent 62%),
    linear-gradient(hsl(var(--foreground) / .02) 1px, transparent 1px),
    linear-gradient(90deg, hsl(var(--foreground) / .02) 1px, transparent 1px);
  background-size: 100% 100%, 40px 40px, 40px 40px;
}
```

Put page content in a wrapper with `position: relative; z-index: 1;` so it sits
above this layer.

---

## 7. Effects & motion — the recipes

| Effect | How |
|---|---|
| **Frosted glass** | `background: hsl(var(--card)/.5)` + `backdrop-filter: blur(9px)` |
| **Neon glow (element)** | `box-shadow: 0 0 24px hsl(<color>/.30)` |
| **Glow (text)** | `text-shadow: 0 0 12px hsl(var(--primary)/.6)` (brand accent letter) |
| **Lit top edge** | `box-shadow: inset 0 1px 0 hsl(0 0% 100%/.18)` |
| **HUD ticks** | corner pseudo-elements (see §4) |
| **Live pulse** | `@keyframes pulse` opacity 1→.35, 1.4s ease-in-out infinite |
| **Press feedback** | `:active { transform: translateY(1px) }` |
| **Focus ring** | double `box-shadow` (bg gap + `--ring`) |

Keep glows subtle (alpha .25–.30). More than a couple of strong glows per screen
kills the effect.

---

## 8. Data visualization — the `Strip` chart

Live line charts are a **hand-rolled `<canvas>` 2D** component (no library). Reuse
this class for any streaming metric (accel, gyro, or your processed data).

```js
const dpr = Math.max(1, window.devicePixelRatio || 1);

class Strip {
  constructor(canvas, colors) {           // colors: ['#22d3ee','#a78bfa','#f472b6']
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this.colors = colors;
    this.N = 220;                          // points kept per series (window)
    this.data = colors.map(() => []);
    this.resize();
  }
  resize() {                               // crisp on retina: back the canvas at dpr
    const c = this.canvas;
    c.width  = Math.max(1, Math.floor(c.clientWidth  * dpr));
    c.height = Math.max(1, Math.floor(c.clientHeight * dpr));
  }
  push(vals) {                             // vals: one number per series
    for (let i = 0; i < this.colors.length; i++) {
      const a = this.data[i];
      a.push((typeof vals[i] === 'number' && isFinite(vals[i])) ? vals[i] : 0);
      if (a.length > this.N) a.shift();
    }
  }
  clear() { this.data = this.colors.map(() => []); }
  draw() {
    const { ctx, canvas: c } = this, W = c.width, H = c.height;
    ctx.clearRect(0, 0, W, H);

    // auto-scale y across all series, +15% padding
    let mn = Infinity, mx = -Infinity;
    for (const a of this.data) for (const v of a) { if (v < mn) mn = v; if (v > mx) mx = v; }
    if (!isFinite(mn)) { mn = -1; mx = 1; }
    if (mn === mx) { mn -= 1; mx += 1; }
    const pad = (mx - mn) * 0.15; mn -= pad; mx += pad;
    const yOf = v => H - ((v - mn) / (mx - mn)) * H;

    // faint zero baseline (only if the range crosses 0)
    ctx.shadowBlur = 0;
    if (mn < 0 && mx > 0) {
      ctx.strokeStyle = 'rgba(255,255,255,0.06)'; ctx.lineWidth = 1;
      ctx.beginPath(); ctx.moveTo(0, yOf(0)); ctx.lineTo(W, yOf(0)); ctx.stroke();
    }

    // series — thin lines, newest hugging the right edge, neon glow
    const step = W / (this.N - 1);
    for (let i = 0; i < this.colors.length; i++) {
      const a = this.data[i];
      if (a.length < 2) continue;
      const offset = W - (a.length - 1) * step;
      ctx.strokeStyle = this.colors[i];
      ctx.lineWidth = 1.25 * dpr;
      ctx.lineJoin = 'round';
      ctx.shadowColor = this.colors[i];
      ctx.shadowBlur = 5 * dpr;             // the glow
      ctx.beginPath();
      for (let j = 0; j < a.length; j++) {
        const x = offset + j * step, y = yOf(a[j]);
        j ? ctx.lineTo(x, y) : ctx.moveTo(x, y);
      }
      ctx.stroke();
    }
  }
}

// wiring: push on your data cadence, draw on a rAF loop
const chart = new Strip(document.getElementById('c1'), ['#22d3ee', '#a78bfa', '#f472b6']);
window.addEventListener('resize', () => chart.resize());
(function loop(){ chart.draw(); requestAnimationFrame(loop); })();
// chart.push([x, y, z]) whenever new data arrives
```

Chart design rules:
- **CSS sets the display size** (`canvas { width:100%; height:90px }`), JS backs it
  at `clientWidth * dpr` for crisp lines.
- **Auto-scaling** y-range keeps any signal readable; **right-aligned** so newest
  data enters from the right.
- **Thin lines** (`1.25 * dpr`) + **glow** (`shadowBlur 5*dpr`) = the neon look.
- Legend is a header row of tiny color chips (`width:10px; height:2px`) matching
  the series colors.

---

## 9. Reproduce it on a new view (checklist)

1. Ship one stylesheet with §2 tokens + §4–§7 classes (copy `ui.css`).
2. `<link rel="stylesheet" href="/ui.css">` and set `<meta name="viewport" content="width=device-width, initial-scale=1">`.
3. Add the `body::before` grid/glow (§6); wrap content in `position:relative; z-index:1`.
4. Build with the primitives: `.card` (+ `.hud` on big panels), `.btn`/`.btn-*`,
   `.badge`/`.badge-live`/`.badge-off` with `.dot`, `.stat` for metrics, `.mono` for numbers.
5. For live plots, drop in the `Strip` class (§8).
6. Stay on-palette: cyan = accent, green = go, red = stop, everything else muted.

---

## 10. Porting to another stack

The system is framework-agnostic — the tokens and rules are what matter:

- **Tailwind / shadcn/ui (React):** paste the §2 triplets into your theme as CSS
  variables (they're already in shadcn's `H S% L%` format), set `--radius: 3px`,
  and map `.btn-success`/`.btn-destructive`/`.btn-outline` onto shadcn `Button`
  variants, `.badge-*` onto `Badge`, `.card`/`.hud` onto `Card`. The look survives
  because it lives in the tokens + the glow/tick/type rules, not the markup.
- **Any framework:** keep the HSL-triplet tokens, the frosted-glass card, the HUD
  ticks, the uppercase-tracked type, the cyan/green/red role split, and the canvas
  `Strip`. Those six things *are* the brand.

## 11. Do / Don't

**Do:** sharp corners (`--radius: 3px`), hairline borders, uppercase tracked
micro-labels, mono tabular numbers, subtle glows, cyan for tech / green for go /
red for stop.

**Don't:** round pills, thick/heavy borders, drop shadows for depth (use glow +
glass instead), cyan on clickable actions, more than ~2 strong glows per screen,
web-font downloads or a charting library (kills the zero-dependency guarantee).
