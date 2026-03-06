from __future__ import annotations


def dashboard_html() -> str:
    return """<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"UTF-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
  <title>Dimnetria Command View</title>
  <style>
    :root {
      --bg: #050d1b;
      --panel: #0c1c33;
      --panel-soft: #102848;
      --line: #1b4e79;
      --text: #d9f4ff;
      --muted: #81a3c7;
      --accent: #4dc8ff;
      --accent-2: #f2a64f;
      --good: #57df9f;
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      font-family: Inter, Segoe UI, Roboto, Helvetica, Arial, sans-serif;
      color: var(--text);
      background:
        radial-gradient(circle at 20% 10%, rgba(77, 200, 255, 0.18), transparent 30%),
        radial-gradient(circle at 80% 90%, rgba(242, 166, 79, 0.17), transparent 30%),
        linear-gradient(180deg, #020814 0%, var(--bg) 100%);
      min-height: 100vh;
      letter-spacing: 0.02em;
    }

    .grid-overlay::before {
      content: "";
      position: fixed;
      inset: 0;
      pointer-events: none;
      background-image:
        linear-gradient(rgba(77, 200, 255, 0.06) 1px, transparent 1px),
        linear-gradient(90deg, rgba(77, 200, 255, 0.06) 1px, transparent 1px);
      background-size: 40px 40px;
      mask-image: linear-gradient(180deg, rgba(0, 0, 0, 0.8), transparent 95%);
    }

    .container {
      width: min(1180px, 95vw);
      margin: 0 auto;
      padding: 2rem 0 2.5rem;
    }

    h1 {
      margin: 0;
      text-transform: uppercase;
      font-size: clamp(1.2rem, 3vw, 2rem);
      letter-spacing: 0.12em;
    }

    .subtitle {
      color: var(--muted);
      margin-top: 0.6rem;
      font-size: 0.95rem;
    }

    .top-cards {
      margin-top: 1.4rem;
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 0.8rem;
    }

    .card {
      border: 1px solid var(--line);
      background: linear-gradient(160deg, rgba(16, 40, 72, 0.8), rgba(12, 28, 51, 0.95));
      border-radius: 10px;
      padding: 0.85rem 1rem;
      box-shadow: inset 0 0 35px rgba(77, 200, 255, 0.07);
    }

    .card .label { font-size: 0.7rem; color: var(--muted); text-transform: uppercase; }
    .card .value { margin-top: 0.4rem; font-size: 1.35rem; font-weight: 650; }

    .main {
      margin-top: 1.2rem;
      display: grid;
      grid-template-columns: 2fr 1fr;
      gap: 0.8rem;
    }

    .map-panel {
      border: 1px solid var(--line);
      border-radius: 12px;
      min-height: 440px;
      background: linear-gradient(160deg, rgba(16, 40, 72, 0.86), rgba(8, 17, 31, 0.98));
      position: relative;
      overflow: hidden;
    }

    .map-title, .list-title {
      position: absolute;
      top: 0.75rem;
      left: 1rem;
      font-size: 0.75rem;
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 0.08em;
      z-index: 2;
    }

    .map-wrap {
      position: absolute;
      inset: 0;
      display: grid;
      place-items: center;
      padding: 2.5rem 1rem 1.2rem;
    }

    svg {
      width: 100%;
      max-width: 760px;
      opacity: 0.95;
      filter: drop-shadow(0 0 8px rgba(77, 200, 255, 0.25));
    }

    .continent { fill: rgba(123, 201, 217, 0.35); stroke: rgba(110, 210, 255, 0.5); stroke-width: 1.5; }
    .route { stroke: rgba(242, 166, 79, 0.6); stroke-width: 1.8; fill: none; stroke-dasharray: 4 7; }

    .hud-right {
      display: grid;
      gap: 0.8rem;
      grid-template-rows: auto 1fr;
    }

    .list-panel, .bar-panel {
      border: 1px solid var(--line);
      border-radius: 12px;
      background: linear-gradient(165deg, rgba(16, 40, 72, 0.9), rgba(8, 17, 31, 0.96));
      position: relative;
      padding: 2.2rem 1rem 1rem;
    }

    .country-list {
      margin: 0;
      padding: 0;
      list-style: none;
      display: grid;
      gap: 0.6rem;
      font-size: 0.9rem;
    }

    .country-list li {
      display: grid;
      grid-template-columns: 1fr auto auto;
      align-items: center;
      gap: 0.5rem;
      background: rgba(6, 14, 26, 0.45);
      border: 1px solid rgba(77, 200, 255, 0.15);
      border-radius: 8px;
      padding: 0.5rem 0.65rem;
    }

    .country-name { color: #d8e6ff; }
    .score { color: var(--good); font-weight: 600; }

    .bar {
      height: 6px;
      width: 100px;
      background: rgba(217, 244, 255, 0.2);
      border-radius: 30px;
      overflow: hidden;
    }

    .bar > span {
      display: block;
      height: 100%;
      background: linear-gradient(90deg, var(--accent), var(--accent-2));
    }

    .distribution {
      margin-top: 0.5rem;
      display: grid;
      gap: 0.3rem;
    }

    .dist-row {
      display: grid;
      grid-template-columns: 44px 1fr 40px;
      align-items: center;
      gap: 0.45rem;
      font-size: 0.78rem;
      color: var(--muted);
    }

    .dist-track {
      height: 9px;
      border-radius: 30px;
      background: rgba(217, 244, 255, 0.17);
      overflow: hidden;
    }

    .dist-fill {
      height: 100%;
      background: linear-gradient(90deg, rgba(77, 200, 255, 0.8), rgba(87, 223, 159, 0.8));
    }

    @media (max-width: 920px) {
      .top-cards { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .main { grid-template-columns: 1fr; }
      .map-panel { min-height: 340px; }
    }
  </style>
</head>
<body class=\"grid-overlay\">
  <div class=\"container\">
    <h1>Dimnetria Live Resilience Deck</h1>
    <div class=\"subtitle\">Function-first command view — the map is the story, the metrics are the proof.</div>

    <section class=\"top-cards\" id=\"kpiCards\"></section>

    <section class=\"main\">
      <article class=\"map-panel\">
        <div class=\"map-title\">Global Signal Map (Illustrative)</div>
        <div class=\"map-wrap\">
          <svg viewBox=\"0 0 900 460\" role=\"img\" aria-label=\"Stylized world map with network routes\">
            <path class=\"continent\" d=\"M115 170l40-40 75-18 60 32 55-14 45 20 20 35-28 20-34 2-28-11-44 17-41-5-20 18-34 5-26-14-20-29z\"/>
            <path class=\"continent\" d=\"M355 265l25-20 28 4 20 16 18 46-16 40-24 9-26-16-18-44z\"/>
            <path class=\"continent\" d=\"M470 148l56-16 80 7 62-22 88 22 42 31-19 24-44 15-24 26-43 6-34 39-30 5-14-22 10-37-18-18-54-2-49 20-45-11-26-30z\"/>
            <path class=\"continent\" d=\"M700 300l35-16 41 3 20 26-8 30-32 17-47-7-20-22z\"/>
            <path class=\"route\" d=\"M125 172 C250 120, 420 110, 566 146\"/>
            <path class=\"route\" d=\"M140 195 C315 270, 510 290, 725 310\"/>
            <path class=\"route\" d=\"M380 286 C430 240, 510 225, 630 235\"/>
          </svg>
        </div>
      </article>

      <section class=\"hud-right\">
        <article class=\"list-panel\">
          <div class=\"list-title\">Top RRFI Countries</div>
          <ul class=\"country-list\" id=\"countryList\"></ul>
        </article>

        <article class=\"bar-panel\">
          <div class=\"list-title\">RRFI Distribution</div>
          <div class=\"distribution\" id=\"distribution\"></div>
        </article>
      </section>
    </section>
  </div>

  <script>
    const average = arr => arr.reduce((a, b) => a + b, 0) / Math.max(arr.length, 1);

    const buildKpis = (results) => {
      const scores = results.map(x => x.rrfi_score);
      const highRisk = results.filter(x => x.rrfi_score < 45).length;
      const cards = [
        {label: 'Countries Tracked', value: results.length},
        {label: 'World Mean RRFI', value: average(scores).toFixed(1)},
        {label: 'High-Risk Count', value: highRisk},
        {label: 'Live Layer Feeds', value: 6}
      ];

      document.getElementById('kpiCards').innerHTML = cards.map(card => `
        <article class=\"card\"><div class=\"label\">${card.label}</div><div class=\"value\">${card.value}</div></article>
      `).join('');
    };

    const buildCountryList = (results) => {
      const sorted = [...results].sort((a, b) => b.rrfi_score - a.rrfi_score).slice(0, 8);
      document.getElementById('countryList').innerHTML = sorted.map(country => `
        <li>
          <span class=\"country-name\">${country.country_name} (${country.iso3})</span>
          <span class=\"score\">${country.rrfi_score.toFixed(1)}</span>
          <div class=\"bar\"><span style=\"width: ${country.rrfi_score}%\"></span></div>
        </li>
      `).join('');
    };

    const buildDistribution = (results) => {
      const bins = [
        {range: '0-20', count: 0},
        {range: '21-40', count: 0},
        {range: '41-60', count: 0},
        {range: '61-80', count: 0},
        {range: '81-100', count: 0}
      ];

      results.forEach(({ rrfi_score }) => {
        const idx = Math.min(4, Math.floor(rrfi_score / 20));
        bins[idx].count += 1;
      });

      const maxCount = Math.max(...bins.map(b => b.count), 1);
      document.getElementById('distribution').innerHTML = bins.map(bin => `
        <div class=\"dist-row\">
          <span>${bin.range}</span>
          <div class=\"dist-track\"><div class=\"dist-fill\" style=\"width:${(bin.count / maxCount) * 100}%\"></div></div>
          <span>${bin.count}</span>
        </div>
      `).join('');
    };

    const load = async () => {
      const response = await fetch('/v1/world/rrfi');
      const payload = await response.json();
      const results = payload.results || [];
      buildKpis(results);
      buildCountryList(results);
      buildDistribution(results);
    };

    load().catch(() => {
      document.getElementById('kpiCards').innerHTML = '<article class="card"><div class="label">Data</div><div class="value">Unavailable</div></article>';
      document.getElementById('countryList').innerHTML = '<li>Could not load RRFI data.</li>';
    });
  </script>
</body>
</html>
"""
