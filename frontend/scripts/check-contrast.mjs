#!/usr/bin/env node
/**
 * Parses tokens.css and asserts WCAG AA contrast for every text × surface
 * combination in both themes. Exits non-zero if any pair fails.
 */
import fs from "node:fs";
import path from "node:path";
import url from "node:url";
import { hex as contrast } from "wcag-contrast";

const __dirname = path.dirname(url.fileURLToPath(import.meta.url));
const cssPath = path.resolve(__dirname, "../src/styles/tokens.css");
const css = fs.readFileSync(cssPath, "utf8");

function parseBlock(css, selector) {
  const re = new RegExp(`${selector}\\s*\\{([^}]+)\\}`, "m");
  const match = css.match(re);
  if (!match) throw new Error(`Selector ${selector} not found in tokens.css`);
  const body = match[1];
  const vars = {};
  for (const line of body.split("\n")) {
    const m = line.match(/--([a-z0-9-]+)\s*:\s*(#[0-9a-fA-F]{3,8})\s*;/);
    if (m) vars[m[1]] = m[2];
  }
  return vars;
}

const light = parseBlock(css, ":root");
const dark  = { ...light, ...parseBlock(css, '\\[data-theme="dark"\\]') };

// Pairs are [fgTokenName, bgTokenName, minRatio, label]
const PAIRS = [
  ["text-primary",   "surface-page",      4.5, "body text on page"],
  ["text-primary",   "surface-card",      4.5, "body text on card"],
  ["text-primary",   "surface-row",       4.5, "body text on row"],
  ["text-secondary", "surface-card",      4.5, "secondary text on card"],
  ["text-muted",     "surface-card",      4.5, "muted text on card"],
  ["text-muted",     "surface-page",      4.5, "muted text on page"],
  ["accent-default", "surface-page",      3.0, "accent on page (non-text)"],
  ["accent-default", "surface-card",      3.0, "accent on card (non-text)"],
  ["accent-fg",      "accent-default",    4.5, "text on accent button"],
  ["success-fg",     "success-bg-soft",   4.5, "success text in pill"],
  ["warning-fg",     "warning-bg-soft",   4.5, "warning text in pill"],
  ["danger-fg",      "danger-bg-soft",    4.5, "danger text in pill"],
  ["info-fg",        "info-bg-soft",      4.5, "info text in pill"],
];

let failed = 0;
for (const [theme, vars] of [["light", light], ["dark", dark]]) {
  for (const [fg, bg, min, label] of PAIRS) {
    const fgHex = vars[fg];
    const bgHex = vars[bg];
    if (!fgHex || !bgHex) {
      console.error(`[${theme}] missing token: ${fg} or ${bg}`);
      failed++;
      continue;
    }
    const ratio = contrast(fgHex, bgHex);
    const pass = ratio >= min;
    const icon = pass ? "PASS" : "FAIL";
    console.log(
      `[${theme}] ${icon} ${label.padEnd(40)} ${fg} on ${bg}  ratio=${ratio.toFixed(2)}  min=${min}`
    );
    if (!pass) failed++;
  }
}

if (failed > 0) {
  console.error(`\nFAILED — ${failed} contrast check(s) did not meet WCAG AA.`);
  process.exit(1);
}
console.log("\nAll contrast checks passed.");
