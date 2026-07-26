#!/usr/bin/env node
// build.js — reads data/results.json, writes dist/index.html
// Run: node scripts/build.js

const fs   = require("fs");
const path = require("path");

const dataPath = path.join(__dirname, "..", "data", "results.json");
const outPath  = path.join(__dirname, "..", "dist", "index.html");

const { query, fetched_at, results } = JSON.parse(fs.readFileSync(dataPath, "utf8"));

const cards = results.map(({ title, summary, url }) => `
  <article class="card">
    <a href="${url}" target="_blank" rel="noopener noreferrer">
      <h2>${title}</h2>
    </a>
    <p>${summary}</p>
  </article>`).join("\n");

const date = new Date(fetched_at).toLocaleDateString("en-US", {
  year: "numeric", month: "long", day: "numeric"
});

const html = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>The History &amp; Resurgence of Pinball</title>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
      background: #0d0d0d;
      color: #f0ece4;
      min-height: 100vh;
      padding: 2rem 1rem 4rem;
    }

    header {
      text-align: center;
      margin-bottom: 3rem;
    }

    header h1 {
      font-size: clamp(1.8rem, 5vw, 3rem);
      letter-spacing: -0.02em;
      background: linear-gradient(135deg, #ff6b35, #ffd23f);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
    }

    header p.meta {
      margin-top: 0.5rem;
      font-size: 0.85rem;
      color: #888;
    }

    .grid {
      max-width: 780px;
      margin: 0 auto;
      display: grid;
      gap: 1.25rem;
    }

    .card {
      background: #1a1a1a;
      border: 1px solid #2a2a2a;
      border-radius: 12px;
      padding: 1.5rem 1.75rem;
      transition: border-color 0.2s, transform 0.15s;
    }

    .card:hover {
      border-color: #ff6b35;
      transform: translateY(-2px);
    }

    .card a {
      text-decoration: none;
      color: inherit;
    }

    .card h2 {
      font-size: 1.05rem;
      font-weight: 600;
      line-height: 1.35;
      color: #ffd23f;
      margin-bottom: 0.6rem;
    }

    .card h2::after {
      content: " ↗";
      font-size: 0.8em;
      opacity: 0.6;
    }

    .card p {
      font-size: 0.92rem;
      line-height: 1.6;
      color: #b0a89e;
    }

    footer {
      text-align: center;
      margin-top: 3rem;
      font-size: 0.78rem;
      color: #555;
    }
  </style>
</head>
<body>
  <header>
    <h1>🎰 The History &amp; Resurgence of Pinball</h1>
    <p class="meta">Top 5 results · sourced ${date}</p>
  </header>

  <main class="grid">
    ${cards}
  </main>

  <footer>Built from <code>data/results.json</code> · query: &ldquo;${query}&rdquo;</footer>
</body>
</html>`;

fs.mkdirSync(path.dirname(outPath), { recursive: true });
fs.writeFileSync(outPath, html, "utf8");
console.log(`✓ Built ${outPath}`);
