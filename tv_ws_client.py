"""
Pure Python TradingView WebSocket Client
单连接多标的实时行情获取 — 无需 Node.js，不限速

用法:
    from tv_ws_client import fetch_realtime_prices
    prices = fetch_realtime_prices(["AAPL", "TSLA", ...])
    # -> {"AAPL": {"price": 308.82, "change_pct": 1.26, "change": 3.83, "volume": 43670223}, ...}
"""

import json
import time
import re
import string
import random
import urllib.request
import ssl
try:
    from websocket import create_connection
    HAS_WS = True
except ImportError:
    HAS_WS = False

WS_URL = "wss://data.tradingview.com/socket.io/websocket"
# HTTP fallback URL for real-time quotes
YAHOO_REALTIME_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=1d"

_NYSE = {
    "JPM", "BAC", "GS", "MS", "V", "MA", "AXP", "KO", "PEP",
    "WMT", "JNJ", "PG", "XOM", "CVX", "UNH", "GE", "CAT", "BA",
    "LMT", "RTX", "MMM", "HON", "T", "VZ", "DIS", "GM", "F",
    "UPS", "FDX", "DAL", "AAL", "GD", "NOC", "IBM", "BRK-B",
    "SPY", "DIA", "GLD", "TLT", "BLK", "C", "WFC", "SCHW",
    "ISRG", "MDT", "SYK", "ABBV", "COP", "OXY", "SLB", "HAL",
    "TMUS", "EL", "YUM", "MCD", "NEE", "TSN", "BRK.B",
}


def get_exchange(ticker: str) -> str:
    return "NYSE" if ticker in _NYSE else "NASDAQ"


def _gen_id(prefix="qs_"):
    chars = string.ascii_lowercase + string.digits
    return prefix + "".join(random.choice(chars) for _ in range(12))


def _msg(func: str, params: list) -> str:
    d = json.dumps({"m": func, "p": params}, separators=(",", ":"))
    return f"~m~{len(d)}~m~{d}"


def fetch_realtime_prices(tickers: list, timeout: float = 30.0) -> dict:
    """
    TradingView WebSocket 实时行情获取

    Returns:
        {ticker: {"price": float, "change_pct": float,
                  "change": float, "volume": int}}
    """
    clean = list(set(tickers))
    sym_map = {}
    for t in clean:
        sym_map[f"{get_exchange(t)}:{t}"] = t
    full_syms = list(sym_map.keys())
    n = len(full_syms)

    ws = create_connection(WS_URL, timeout=10, skip_utf8_validation=True)
    ws.settimeout(1)

    # 初始化连接
    try: ws.recv()
    except: pass

    # 认证 + 创建 session
    ws.send(_msg("set_auth_token", ["unauthorized_user_token"]))
    time.sleep(0.15)
    try: ws.recv()
    except: pass

    s = _gen_id()
    ws.send(_msg("quote_create_session", [s]))
    time.sleep(0.15)
    try: ws.recv()
    except: pass

    # 设置字段
    ws.send(_msg("quote_set_fields", [s, "lp", "chp", "ch", "volume"]))
    time.sleep(0.15)
    try: ws.recv()
    except: pass

    # 逐个添加符号
    for sym in full_syms:
        ws.send(_msg("quote_add_symbols", [s, [sym]]))
    time.sleep(0.3)

    # 快速订阅
    ws.send(_msg("quote_fast_symbols", [s, full_syms]))

    # 收集结果
    results = {}
    start = time.time()
    while len(results) < n and (time.time() - start) < timeout:
        try:
            raw = ws.recv()
            if not raw or "qsd" not in raw:
                continue

            pos = 0
            while pos < len(raw):
                m = re.search(r'~m~(\d+)~m~', raw[pos:])
                if not m:
                    break
                length = int(m.group(1))
                data_start = pos + m.end()
                if data_start + length > len(raw):
                    break
                data = raw[data_start:data_start + length]
                pos = data_start + length

                try:
                    j = json.loads(data)
                except json.JSONDecodeError:
                    continue

                if j.get("m") != "qsd":
                    continue
                p = j.get("p", [])
                if len(p) < 2:
                    continue
                val = p[1]
                if not isinstance(val, dict):
                    continue
                full_name = val.get("n", "")
                if full_name not in sym_map or full_name in results:
                    continue
                v = val.get("v", {})
                lp = v.get("lp")
                if lp is not None:
                    results[full_name] = {
                        "price": float(lp),
                        "change_pct": float(v.get("chp", 0)),
                        "change": float(v.get("ch", 0)),
                        "volume": int(float(v.get("volume", 0))),
                    }
        except Exception:
            continue

    ws.close()

    out = {}
    for full, orig in sym_map.items():
        if full in results:
            out[orig] = results[full]
    return out


def fetch_realtime_http(tickers: list, timeout: float = 30.0) -> dict:
    """HTTP 实时行情 — Yahoo Finance 实时报价
    并行抓取，速度快、覆盖广、无外部依赖
    """
    import concurrent.futures
    out = {}
    # 根据池大小动态调整 — 大池用更多worker
    workers = min(40, max(20, len(tickers) // 5))

    def _fetch_one(tkr):
        try:
            url = YAHOO_REALTIME_URL.format(ticker=tkr)
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                "Accept": "application/json",
            })
            # 每次请求独立超时 = total_timeout / 批次
            req_timeout = max(8, min(20, timeout / (len(tickers) / workers + 1)))
            resp = urllib.request.urlopen(req, timeout=req_timeout, context=ctx)
            data = json.loads(resp.read().decode())
            ch = data.get("chart", {}).get("result", [])
            if not ch:
                return None
            meta = ch[0].get("meta", {})
            indic = ch[0].get("indicators", {}).get("quote", [{}])
            if not indic:
                return None
            q = indic[0]
            closes = q.get("close", [])
            vols = q.get("volume", [])
            if not closes or not closes[-1]:
                return None
            price = float(closes[-1])
            prev_close = float(meta.get("chartPreviousClose", 0) or meta.get("previousClose", price))
            change = price - prev_close
            change_pct = (change / prev_close) * 100 if prev_close else 0
            volume = int(vols[-1]) if vols and vols[-1] else 0
            return {
                "price": price,
                "change_pct": round(change_pct, 2),
                "change": round(change, 2),
                "volume": volume,
            }
        except Exception:
            return None

    clean = list(set(tickers))
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        fut_map = {pool.submit(_fetch_one, t): t for t in clean}
        for fut in concurrent.futures.as_completed(fut_map, timeout=timeout):
            t = fut_map[fut]
            try:
                r = fut.result()
                if r:
                    out[t] = r
            except Exception:
                continue
    return out
