"""
美股扫描分析 App — FastAPI 后端
实时扫描美股市场，基于知识库书籍给出前10做多/做空排名
"""
import sys, os, json, time, asyncio
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

# 添加项目到路径
sys.path.insert(0, str(Path(__file__).parent))
from scanner import compute_indicators, SCAN_UNIVERSE, CN_NAME_MAP, SECTOR_MAP, search_stocks, fetch_all_tv

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
    """执行全市场扫描 — TradingView 实时数据"""
    return fetch_all_tv()


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


@app.get("/api/diag")
async def api_diag():
    """诊断端点 — 测试数据源连通性"""
    from tv_ws_client import fetch_realtime_prices, fetch_realtime_http
    import time
    diag = {"timestamp": datetime.now().isoformat()}

    # 测试 WebSocket
    test_tickers = ["AAPL", "MSFT", "TSLA", "GOOGL", "AMZN"]
    try:
        t0 = time.time()
        ws_data = fetch_realtime_prices(test_tickers, timeout=10)
        ws_time = time.time() - t0
        diag["ws_status"] = "ok" if len(ws_data) >= 2 else "partial"
        diag["ws_count"] = len(ws_data)
        diag["ws_time"] = round(ws_time, 2)
        diag["ws_sample"] = ws_data
    except Exception as e:
        diag["ws_status"] = "error"
        diag["ws_error"] = str(e)

    # 测试 HTTP 备份
    try:
        t0 = time.time()
        http_data = fetch_realtime_http(test_tickers, timeout=10)
        http_time = time.time() - t0
        diag["http_status"] = "ok" if len(http_data) >= 2 else "partial"
        diag["http_count"] = len(http_data)
        diag["http_time"] = round(http_time, 2)
        diag["http_sample"] = http_data
    except Exception as e:
        diag["http_status"] = "error"
        diag["http_error"] = str(e)

    diag["universe_count"] = len(SCAN_UNIVERSE)
    return diag


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
