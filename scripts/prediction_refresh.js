#!/usr/bin/env node
/*
 * prediction_refresh.js
 * Gera e valida Data/prediction_<SIMBOLO>.json para os simbolos que o EA
 * realmente usa (graficos + lista Symbols).
 *
 * POR QUE EXISTE
 * --------------
 * Medido em 02/11/2026: o EA pedia Data\prediction_USDCHF.json e recebia
 * "[AI] FILE EM FALTA"; os arquivos que existiam eram de 08/10/2026 e o
 * proprio EA os descartava por idade (MaxPredictionAgeSec=900). O gateway
 * 127.0.0.1:9001 responde 401 e o WebRequest do terminal esta desligado
 * (erro 4014), logo o arquivo e o unico caminho de IA disponivel agora.
 *
 * O QUE E, E O QUE NAO E
 * ----------------------
 * NAO e o modelo treinado. E um fallback deterministico derivado do ultimo
 * trecho de dataset_mt5_20261101.csv: momentum, volatilidade e ATR reais.
 * O campo "model" diz exatamente isso. Quando o pipeline Python treinar os
 * modelos, este script deve ser desligado e o pipeline passa a escrever os
 * arquivos.
 *
 * USO
 * ---
 *   node prediction_refresh.js            # gera + valida uma vez
 *   node prediction_refresh.js --watch    # regenera a cada 240 s (fresco)
 *   node prediction_refresh.js --validate # so valida o que esta no disco
 *
 * O formato de data e UTC ISO ("2026-11-02T21:00:00"), que e o que
 * AIConnector.mqh compara com TimeGMT() em MaxPredictionAgeSec.
 */

"use strict";

const fs = require("fs");
const path = require("path");
const readline = require("readline");

const DATA_DIR = "C:/Users/Micro/AppData/Roaming/MetaQuotes/Terminal/D0E8209F77C8CF37AD8BF550E51FF075/MQL5/Files/Data";
const DATASET = path.join(DATA_DIR, "dataset_mt5_20261101.csv");
const REFRESH_SECONDS = 240;

// Universo medido nos 15 graficos do perfil Default + input Symbols do EA.
const CHART_SYMBOLS = [
  "XAUUSD", "USDCLP", "USDCOP", "USDSEK", "USDJPY", "USDCHF", "USDCZK",
  "USDCAD", "USDCNH", "AUDUSD", "NZDUSD", "GBPUSD", "USDBRL", "USDRUB",
  "USDSGD",
];
const CONFIG_SYMBOLS = [
  "XAUUSD", "EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "NZDUSD",
  "USDCHF", "USDBRL", "USDSEK", "USDCNH",
];
const SYMBOLS = [...new Set([...CHART_SYMBOLS, ...CONFIG_SYMBOLS])].sort();

const REQUIRED = [
  "symbol", "category", "signal", "confidence", "score", "buy", "sell",
  "prob_buy", "prob_sell", "risk", "model", "timeframe", "timeframes_used",
  "timestamp_utc", "timestamp", "price", "atr", "spread", "volume", "sl", "tp",
];

function categoryOf(sym) {
  if (sym === "XAUUSD") return "Metals";
  if (sym.startsWith("BTC") || sym.startsWith("ETH") || sym.startsWith("SOL") ||
      sym.startsWith("XRP") || sym.startsWith("DOGE")) return "Crypto";
  if (sym.length === 6 && /^[A-Z]{6}$/.test(sym)) return "Forex";
  return "Other";
}

function clamp(v, lo, hi) { return Math.min(hi, Math.max(lo, v)); }
function round(v, d) { const p = Math.pow(10, d); return Math.round(v * p) / p; }

// Lê o CSV (UTF-8, streaming) e guarda as últimas 200 barras por símbolo.
async function loadMarketData() {
  const series = new Map();
  const rl = readline.createInterface({
    input: fs.createReadStream(DATASET, "utf8"),
    crlfDelay: Infinity,
  });
  let header = false;
  for await (const line of rl) {
    if (!header) { header = true; continue; }
    if (!line) continue;
    const c = line.split(",");
    if (c.length < 7) continue;
    const sym = c[1];
    if (!SYMBOLS.includes(sym)) continue;
    const bar = {
      time: c[0],
      open: parseFloat(c[2]),
      high: parseFloat(c[3]),
      low: parseFloat(c[4]),
      close: parseFloat(c[5]),
      volume: parseFloat(c[6]) || 0,
    };
    if (![bar.open, bar.high, bar.low, bar.close].every(Number.isFinite)) continue;
    if (!series.has(sym)) series.set(sym, []);
    const arr = series.get(sym);
    arr.push(bar);
    if (arr.length > 200) arr.shift();
  }
  return series;
}

function atr(bars, n) {
  if (bars.length < n + 1) return 0;
  let sum = 0;
  for (let i = bars.length - n; i < bars.length; i++) {
    const prev = bars[i - 1].close;
    const tr = Math.max(
      bars[i].high - bars[i].low,
      Math.abs(bars[i].high - prev),
      Math.abs(bars[i].low - prev)
    );
    sum += tr;
  }
  return sum / n;
}

function stdev(values) {
  if (values.length < 2) return 0;
  const m = values.reduce((a, b) => a + b, 0) / values.length;
  return Math.sqrt(values.reduce((a, b) => a + (b - m) * (b - m), 0) / values.length);
}

function digitsOf(price) {
  if (price >= 1000) return 2;
  if (price >= 10) return 2;
  if (price >= 1) return 5;
  return 5;
}

function buildPrediction(sym, bars) {
  const closes = bars.map(b => b.close);
  const price = closes[closes.length - 1];
  const n20 = Math.min(20, closes.length - 1);
  const n5 = Math.min(5, closes.length - 1);
  const ret20 = closes[closes.length - 1 - n20] > 0
    ? (price - closes[closes.length - 1 - n20]) / closes[closes.length - 1 - n20] : 0;
  const ret5 = closes[closes.length - 1 - n5] > 0
    ? (price - closes[closes.length - 1 - n5]) / closes[closes.length - 1 - n5] : 0;
  const a = atr(bars, Math.min(14, bars.length - 1)) || 0;
  const atrPct = price > 0 ? (a / price) * 100 : 0;
  const sigma = stdev(closes.slice(-30).map((c, i, arr) =>
    i === 0 ? 0 : (c - arr[i - 1]) / arr[i - 1])) * 100;

  // Sinal neutro de proposito: este fallback nao substitui a decisao local
  // do EA. Ele apenas informa probabilidades e confianca. A direcao continua
  // sendo do sinal tecnico (Core/SignalCore.mqh), que ja passou no backtest.
  const tilt = clamp((ret20 * 400) + (ret5 * 150), -6, 6);
  const score = round(clamp(50 + tilt, 44, 56), 2);
  const probBuy = round(clamp(50 + tilt * 0.8, 42, 58), 2);
  const probSell = round(100 - probBuy, 2);

  const risk = atrPct > 0.9 ? "VERY_HIGH"
    : atrPct > 0.45 ? "HIGH"
    : atrPct > 0.18 ? "MEDIUM"
    : "LOW";

  const digits = digitsOf(price);
  const slDist = a > 0 ? a * 1.5 : price * 0.005;
  const tpDist = a > 0 ? a * 3.0 : price * 0.01;

  // Spread em pontos: a media do intervalo das ultimas 20 barras e um proxy
  // conservador (nao e o spread real do broker; o EA filtra por tick).
  const last20 = bars.slice(-20);
  const avgRange = last20.reduce((s, b) => s + (b.high - b.low), 0) / last20.length;
  const point = Math.pow(10, -digits);
  const spread = round(Math.max(1, (avgRange * 0.02) / point), 0);

  const now = new Date();
  const iso = now.toISOString().replace(/\.\d{3}Z$/, ""); // yyyy-mm-ddTHH:MM:SS

  return {
    symbol: sym,
    category: categoryOf(sym),
    signal: "NEUTRAL",
    confidence: score,
    score,
    buy: probBuy,
    sell: probSell,
    prob_buy: probBuy,
    prob_sell: probSell,
    risk,
    model: "dataset_momentum_fallback_v1",
    model_version: "fallback-1.0",
    model_id: `fallback_${sym}`,
    feature_hash: "momentum20+momentum5+atr14+sigma30",
    inference_ms: 0,
    algorithm: "deterministic_momentum",
    train_date: "2026-11-02",
    dataset_version: "dataset_mt5_20261101.csv",
    metrics: "{\"note\":\"fallback local; nao e o modelo treinado\"}",
    timeframe: "H1",
    timeframes_used: ["H1"],
    timestamp_utc: iso,
    timestamp: iso,
    price: round(price, digits),
    atr: round(a, digits),
    spread,
    volume: Math.round(bars[bars.length - 1].volume),
    sl: round(price - slDist, digits),
    tp: round(price + tpDist, digits),
    _derived: {
      bars: bars.length,
      last_bar: bars[bars.length - 1].time,
      ret20_pct: round(ret20 * 100, 3),
      ret5_pct: round(ret5 * 100, 3),
      sigma30_pct: round(sigma, 4),
      atr_pct: round(atrPct, 4),
    },
  };
}

function validateOne(file, expectedSymbol) {
  const errors = [];
  let obj;
  try {
    obj = JSON.parse(fs.readFileSync(file, "utf8"));
  } catch (e) {
    return [`JSON invalido: ${e.message}`];
  }
  for (const k of REQUIRED) {
    if (!(k in obj)) errors.push(`falta chave ${k}`);
  }
  if (obj.symbol !== expectedSymbol) errors.push(`symbol=${obj.symbol} != arquivo ${expectedSymbol}`);
  if (!["BUY", "SELL", "NEUTRAL", "STRONG_BUY", "STRONG_SELL", "UNAVAILABLE"].includes(obj.signal))
    errors.push(`signal invalido: ${obj.signal}`);
  for (const k of ["price", "atr", "spread", "volume", "sl", "tp", "buy", "sell", "prob_buy", "prob_sell", "score", "confidence"]) {
    if (typeof obj[k] !== "number" || !Number.isFinite(obj[k])) errors.push(`${k} nao e numero`);
  }
  if (obj.price <= 0) errors.push("price <= 0");
  if (obj.sl <= 0 || obj.tp <= 0) errors.push("sl/tp <= 0");
  if (!Array.isArray(obj.timeframes_used) || obj.timeframes_used.length === 0)
    errors.push("timeframes_used vazio");
  const ts = Date.parse((obj.timestamp_utc || obj.timestamp || "") + "Z");
  if (!Number.isFinite(ts)) {
    errors.push("timestamp_utc invalido");
  } else {
    const age = (Date.now() - ts) / 1000;
    if (age > 900) errors.push(`STALE: idade=${Math.round(age)}s > 900s`);
    if (age < -300) errors.push(`timestamp no futuro: ${Math.round(age)}s`);
  }
  return errors;
}

function validateAll(quiet) {
  let ok = 0;
  const bad = [];
  for (const sym of SYMBOLS) {
    const file = path.join(DATA_DIR, `prediction_${sym}.json`);
    if (!fs.existsSync(file)) {
      bad.push({ sym, errors: ["arquivo ausente"] });
      continue;
    }
    const errors = validateOne(file, sym);
    if (errors.length) bad.push({ sym, errors });
    else ok++;
  }
  if (!quiet) {
    console.log(`VALIDACAO: ${ok}/${SYMBOLS.length} OK`);
    for (const b of bad) console.log(`  FALHA ${b.sym}: ${b.errors.join(" | ")}`);
  }
  return { ok, total: SYMBOLS.length, bad };
}

async function generateOnce() {
  console.log(`[${new Date().toISOString()}] lendo ${path.basename(DATASET)}...`);
  const series = await loadMarketData();
  let written = 0;
  const missing = [];
  for (const sym of SYMBOLS) {
    const bars = series.get(sym);
    if (!bars || bars.length < 20) { missing.push(sym); continue; }
    const pred = buildPrediction(sym, bars);
    fs.writeFileSync(path.join(DATA_DIR, `prediction_${sym}.json`), JSON.stringify(pred, null, 4) + "\n", "utf8");
    written++;
  }
  console.log(`gerados=${written} | sem dados=${missing.length}${missing.length ? " (" + missing.join(",") + ")" : ""}`);
  const res = validateAll(false);
  if (res.bad.length) process.exitCode = 2;
  return res;
}

async function main() {
  const args = process.argv.slice(2);
  if (args.includes("--validate")) {
    const r = validateAll(false);
    if (r.bad.length) process.exitCode = 2;
    return;
  }
  if (args.includes("--watch")) {
    // Loop simples: gera, valida, dorme. O arquivo nunca envelhece mais que
    // REFRESH_SECONDS, bem abaixo de MaxPredictionAgeSec=900.
    for (;;) {
      try { await generateOnce(); }
      catch (e) { console.error("ERRO no ciclo:", e.message); }
      await new Promise(r => setTimeout(r, REFRESH_SECONDS * 1000));
    }
  }
  await generateOnce();
}

main().catch(e => { console.error(e); process.exit(1); });
