/**
 * tv_scanner.js — TradingView 全量数据获取 v2
 * 共享单连接，避免 Rate Limit (429)
 *
 * 用法: node tv_scanner.js < tickers.json
 * 或者: node tv_scanner.js '[ "AAPL", "TSLA", ... ]'
 *
 * 输出到 stdout: JSON 数组
 * 每只: { ticker, last_price, prev_close, open, high, low, volume,
 *         change, change_pct, description,
 *         hist_close[], hist_high[], hist_low[], hist_volume[] }
 */

const TradingView = require('@mathieuc/tradingview');

// 解析输入
let tickers;
try {
  const raw = process.argv[2] || '';
  if (raw.startsWith('[')) {
    tickers = JSON.parse(raw);
  } else {
    const fs = require('fs');
    tickers = JSON.parse(fs.readFileSync(raw, 'utf8'));
  }
} catch (e) {
  console.error('Usage: node tv_scanner.js <JSON_ARRAY_OR_FILE>');
  process.exit(1);
}

if (!tickers.length) { console.error('Empty tickers'); process.exit(1); }

const MAX_CONCURRENT = 8;
const TIMEOUT_MS = 20000;

// 搜索缓存
const exchangeCache = {};
async function findSymbol(ticker) {
  if (exchangeCache[ticker]) return exchangeCache[ticker];
  try {
    const results = await TradingView.searchMarket(ticker);
    const match = results.find(r => r.symbol.toUpperCase() === ticker.toUpperCase());
    if (match) {
      exchangeCache[ticker] = match.exchange + ':' + match.symbol;
      return exchangeCache[ticker];
    }
    if (results.length > 0) {
      exchangeCache[ticker] = results[0].exchange + ':' + results[0].symbol;
      return exchangeCache[ticker];
    }
  } catch (_) {}
  exchangeCache[ticker] = null;
  return null;
}

// 用共享 client 获取单只股票
// (已内联到 main 中)

async function main() {
  // Step 1: 解析交易所
  process.stderr.write(`Resolving ${tickers.length} symbols...\n`);
  const results = await Promise.allSettled(tickers.map(t => findSymbol(t)));
  const fullSymbols = tickers.map((t, i) => ({
    ticker: t,
    full: results[i].status === 'fulfilled' && results[i].value
      ? results[i].value
      : 'NASDAQ:' + t
  }));

  process.stderr.write(`Fetching ${fullSymbols.length} stocks (concurrency=${MAX_CONCURRENT})...\n`);

  // Step 2: 分块，每块换新连接避免 Session 老化
  const CHUNK = 40;
  const out = [];
  for (let chunkStart = 0; chunkStart < fullSymbols.length; chunkStart += CHUNK) {
    const chunk = fullSymbols.slice(chunkStart, chunkStart + CHUNK);
    process.stderr.write(`Chunk ${chunkStart / CHUNK + 1}: ${chunk.length} stocks (new connection)\n`);

    const chunkClient = new TradingView.Client();
    
    for (let i = 0; i < chunk.length; i += MAX_CONCURRENT) {
      const batch = chunk.slice(i, i + MAX_CONCURRENT);
      const promises = batch.map(s => {
        return new Promise((resolve) => {
          let done = false;
          const chart = new chunkClient.Session.Chart();
          chart.setMarket(s.full, { timeframe: 'D' });
          chart.onError(() => { if (!done) { done = true; resolve(null); } });
          chart.onUpdate(() => {
            if (done) return;
            if (!chart.periods || !chart.periods[0]) return;
            const periods = chart.periods;
            const latest = periods[0];
            const prev = periods[1] || latest;
            const sorted = [...periods].reverse();
            const last_price = latest.close;
            const prev_close = prev.close;
            const change = last_price - prev_close;
            const change_pct = prev_close > 0 ? (change / prev_close) * 100 : 0;
            done = true;
            resolve({
              ticker: s.ticker,
              description: chart.infos.description || '',
              last_price, prev_close, open: latest.open,
              high: latest.max, low: latest.min, volume: latest.volume,
              change: Math.round(change * 100) / 100,
              change_pct: Math.round(change_pct * 100) / 100,
              hist_close: sorted.map(p => p.close),
              hist_high: sorted.map(p => p.max),
              hist_low: sorted.map(p => p.min),
              hist_volume: sorted.map(p => p.volume),
            });
          });
          setTimeout(() => { if (!done) { done = true; resolve(null); } }, TIMEOUT_MS);
        });
      });

      const batchResults = await Promise.allSettled(promises);
      for (const r of batchResults) {
        if (r.status === 'fulfilled' && r.value) out.push(r.value);
      }
      process.stderr.write(`  ${Math.min(chunkStart + i + MAX_CONCURRENT, fullSymbols.length)}/${fullSymbols.length} (${out.length} OK)\n`);
      await new Promise(r => setTimeout(r, 500));
    }
    
    chunkClient.end();
  }

  process.stderr.write(`Done: ${out.length}/${fullSymbols.length} stocks\n`);
  process.stdout.write(JSON.stringify(out));
}

main().catch(e => {
  process.stderr.write('Fatal: ' + e.message + '\n');
  process.exit(1);
});
