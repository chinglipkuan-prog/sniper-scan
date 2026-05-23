"""
美股扫描分析 App — FastAPI 后端
实时扫描美股市场，基于知识库书籍给出前10做多/做空排名
"""
import sys, os, json, time, asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

# 添加项目到路径
sys.path.insert(0, str(Path(__file__).parent))
from scanner import compute_indicators, SCAN_UNIVERSE, CN_NAME_MAP, SECTOR_MAP, search_stocks

app = FastAPI(title="美股狙击扫描器", version="1.0.0")

# 挂载静态文件
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# 缓存
scan_cache = {}
CACHE_DURATION = 120  # 缓存有效期（秒）
scan_lock = asyncio.Lock()

# 线程池 — yfinance 同步调用
executor = ThreadPoolExecutor(max_workers=8)

HTML_DIR = Path(__file__).parent / "templates"


def _run_scan():
    """执行全市场扫描"""
    batch_size = 20
    results = []
    total = len(SCAN_UNIVERSE)

    for i in range(0, total, batch_size):
        batch = SCAN_UNIVERSE[i:i + batch_size]
        batch_results = []
        for ticker in batch:
            try:
                r = compute_indicators(ticker)
                if r:
                    batch_results.append(r)
            except Exception:
                pass
            time.sleep(0.15)  # yfinance 限速
        results.extend(batch_results)

    # 分类排名
    buys_all = sorted([r for r in results if r["direction"] == "buy"],
                      key=lambda x: x["bullish_score"], reverse=True)
    sells_all = sorted([r for r in results if r["direction"] == "sell"],
                       key=lambda x: x["bearish_score"], reverse=True)

    # 去重：同一只股票不会同时出现在做多和做空里
    # 但如果一只票做多和做空分差 < 15，两边都列但降低排名
    buys_filtered = []
    for b in buys_all:
        dup_sell = [s for s in sells_all if s["ticker"] == b["ticker"]]
        if dup_sell and abs(b["bullish_score"] - dup_sell[0]["bearish_score"]) < 15:
            # 争议票只列出一次，方向以高分决定
            if b["bullish_score"] >= dup_sell[0]["bearish_score"]:
                buys_filtered.append(b)
            # 否则这个票在 sells 里出现，跳过
        else:
            buys_filtered.append(b)

    sells_filtered = []
    for s in sells_all:
        dup_buy = [b for b in buys_all if b["ticker"] == s["ticker"]]
        if dup_buy and abs(s["bearish_score"] - dup_buy[0]["bullish_score"]) < 15:
            if s["bearish_score"] > dup_buy[0]["bullish_score"]:
                sells_filtered.append(s)
        else:
            sells_filtered.append(s)

    return {
        "buys": buys_filtered[:10],
        "sells": sells_filtered[:10],
        "total_scanned": len(results),
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/api/scan")
async def api_scan(refresh: bool = Query(False)):
    """全市场扫描 — 返回前10做多 + 前10做空"""
    global scan_cache

    now = time.time()
    if not refresh and "data" in scan_cache and (now - scan_cache["time"]) < CACHE_DURATION:
        return scan_cache["data"]

    async with scan_lock:
        # 双重检查
        if not refresh and "data" in scan_cache and (now - scan_cache["time"]) < CACHE_DURATION:
            return scan_cache["data"]

        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(executor, _run_scan)
        scan_cache = {"data": data, "time": time.time()}
        return data


@app.get("/api/stock/{ticker}")
async def api_stock(ticker: str):
    """单只股票详细分析"""
    result = compute_indicators(ticker.upper())
    if result:
        return {"found": True, "stock": result}
    return {"found": False, "ticker": ticker.upper()}


@app.get("/api/search")
async def api_search(q: str = Query("")):
    """搜索股票"""
    matches = search_stocks(q)
    return {"results": matches}


@app.get("/api/universe")
async def api_universe():
    """返回全量扫描池"""
    stocks = []
    for ticker in SCAN_UNIVERSE:
        stocks.append({
            "ticker": ticker,
            "name": CN_NAME_MAP.get(ticker, ticker),
            "sector": SECTOR_MAP.get(ticker, "其他"),
        })
    return {"stocks": stocks}


@app.get("/splash", response_class=HTMLResponse)
async def splash():
    """启动画面"""
    html_path = HTML_DIR / "splash.html"
    if html_path.exists():
        return HTMLResponse(html_path.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>Splash 文件未找到</h1>")

@app.get("/", response_class=HTMLResponse)
async def index():
    """主页面"""
    html_path = HTML_DIR / "index.html"
    if html_path.exists():
        return HTMLResponse(html_path.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>UI 文件未找到</h1>")


@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0", "time": datetime.now().isoformat()}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
