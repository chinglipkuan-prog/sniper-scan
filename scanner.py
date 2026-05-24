"""
美股扫描分析引擎
基于知识库书籍实现：
  - 短线交易大师：高胜率模型、交易心理
  - 短线狙击手：精准入场点、爆发性捕捉
  - 股票K线炼金术：K线形态、主力意图
  - 盘口：量价关系、盘口解读
  - 同花顺实战精要系列：MACD/RSI、量价分析、分时技法
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import time

# ============================================================
# 扫描池 - 覆盖所有主要行业的 100+ 只美股
# ============================================================
SCAN_UNIVERSE = [
    # --- 科技巨头 ---
    "AAPL", "MSFT", "GOOGL", "GOOG", "AMZN", "META", "NVDA", "TSLA",
    # --- 半导体 ---
    "AMD", "INTC", "QCOM", "TXN", "AVGO", "ASML", "MU", "MRVL", "NXPI", "AMAT", "LRCX", "KLAC",
    # --- 软件/SaaS ---
    "CRM", "ORCL", "ADBE", "NOW", "INTU", "SAP", "UBER", "PYPL", "SQ", "SHOP", "DDOG", "SNOW", "MDB", "NET",
    # --- 互联网 ---
    "BABA", "PDD", "JD", "BIDU", "MELI", "SE", "SNAP", "PINS", "RDDT", "ARM",
    # --- AI/算力/存储 ---
    "SMCI", "DELL", "HPQ", "STX", "WDC",
    # --- 加密货币相关 ---
    "COIN", "MARA", "RIOT", "MSTR",
    # --- 医药/生物 ---
    "PFE", "MRK", "ABBV", "JNJ", "UNH", "LLY", "IBRX", "NVAX", "MRNA", "BIIB", "GILD", "AMGN", "REGN", "VRTX",
    # --- 金融/银行 ---
    "JPM", "GS", "MS", "BAC", "WFC", "C", "V", "MA", "AXP", "SCHW", "BLK",
    # --- 消费/零售 ---
    "WMT", "COST", "HD", "LOW", "NKE", "SBUX", "MCD", "TGT", "DG", "DLTR", "CHWY",
    # --- 电信/媒体 ---
    "T", "VZ", "CMCSA", "DIS", "NFLX", "WBD", "LYV", "SPOT",
    # --- 能源 ---
    "XOM", "CVX", "COP", "SLB", "OXY", "EOG", "HAL", "PSX", "VLO",
    # --- 工业/国防 ---
    "CAT", "BA", "GE", "HON", "MMM", "LMT", "RTX", "GD", "NOC",
    # --- 汽车/运输 ---
    "F", "GM", "RIVN", "LCID", "NIO", "LI", "XPEV", "DASH",
    # --- 网安 ---
    "PANW", "CRWD", "FTNT", "ZS",
    # --- 大数据/AI ---
    "PLTR", "SOUN",
    # --- 云计算/企服 ---
    "WDAY", "TEAM",
    # --- 消费饮料/食品 ---
    "KO", "PEP", "PM", "EL", "YUM", "MDLZ",
    # --- 零售 ---
    "TJX", "ROST", "ORLY", "AZO", "TSCO",
    # --- 医疗设备 ---
    "ISRG", "MDT", "BSX", "SYK", "ZTS",
    # --- 保险 ---
    "BRK-B", "ALL", "MET", "PRU",
    # --- 工业补充 ---
    "CARR", "OTIS", "PWR", "CMI", "ITW",
    # --- 航空 ---
    "DAL", "UAL", "LUV",
    # --- 新能源/清洁能源 ---
    "ENPH", "FSLR", "NEE",
    # --- 游戏/娱乐 ---
    "EA", "TTWO", "ROKU",
    # --- 物流/快递 ---
    "FDX", "UPS",
    # --- 电信 ---
    "TMUS",
    # --- 热门金融科技 ---
    "HOOD", "SOFI", "AFRM",
    # --- 半导体补充 ---
    "TSM",
    # --- 中概股补充 ---
    "BILI", "TCOM",
    # --- 其它重要 ---
    "SONY", "CVS",
    # --- ETF补充 ---
    "VTI", "TLT", "GLD", "SLV", "KWEB",
]

# 行业映射
SECTOR_MAP = {
    "AAPL":"科技", "MSFT":"科技", "GOOGL":"科技", "GOOG":"科技", "AMZN":"消费/云", "META":"科技", "NVDA":"半导体", "TSLA":"汽车",
    "AMD":"半导体", "INTC":"半导体", "QCOM":"半导体", "TXN":"半导体", "AVGO":"半导体", "ASML":"半导体", "MU":"半导体", "MRVL":"半导体",
    "NXPI":"半导体", "AMAT":"半导体", "LRCX":"半导体", "KLAC":"半导体",
    "CRM":"软件", "ORCL":"软件", "ADBE":"软件", "NOW":"软件", "INTU":"软件", "SAP":"软件", "UBER":"出行", "PYPL":"金融科技", "SQ":"金融科技",
    "SHOP":"电商", "DDOG":"云", "SNOW":"数据", "MDB":"数据", "NET":"网络",
    "BABA":"电商", "PDD":"电商", "JD":"电商", "BIDU":"互联网", "MELI":"电商", "SE":"互联网", "SNAP":"社交", "PINS":"社交", "RDDT":"社交", "ARM":"半导体",
    "SMCI":"算力", "DELL":"硬件", "HPQ":"硬件", "STX":"存储", "WDC":"存储",
    "COIN":"加密货币", "MARA":"加密货币", "RIOT":"加密货币", "MSTR":"加密货币",
    "PFE":"医药", "MRK":"医药", "ABBV":"医药", "JNJ":"医药", "UNH":"医疗", "LLY":"医药", "IBRX":"生物科技", "NVAX":"生物科技",
    "MRNA":"生物科技", "BIIB":"生物科技", "GILD":"医药", "AMGN":"医药", "REGN":"医药", "VRTX":"医药",
    "JPM":"银行", "GS":"投行", "MS":"投行", "BAC":"银行", "WFC":"银行", "C":"银行", "V":"支付", "MA":"支付", "AXP":"金融", "SCHW":"券商", "BLK":"资管",
    "WMT":"零售", "COST":"零售", "HD":"零售", "LOW":"零售", "NKE":"消费", "SBUX":"消费", "MCD":"消费", "TGT":"零售", "DG":"零售", "DLTR":"零售", "CHWY":"电商",
    "T":"电信", "VZ":"电信", "CMCSA":"媒体", "DIS":"媒体", "NFLX":"流媒体", "WBD":"媒体", "LYV":"娱乐", "SPOT":"音乐",
    "XOM":"能源", "CVX":"能源", "COP":"能源", "SLB":"油服", "OXY":"能源", "EOG":"能源", "HAL":"油服", "PSX":"能源", "VLO":"能源",
    "CAT":"工业", "BA":"航空", "GE":"工业", "HON":"工业", "MMM":"工业", "LMT":"国防", "RTX":"国防", "GD":"国防", "NOC":"国防",
    "F":"汽车", "GM":"汽车", "RIVN":"电动车", "LCID":"电动车", "NIO":"电动车", "LI":"电动车", "XPEV":"电动车", "DASH":"外卖",
    "SPY":"大盘ETF", "QQQ":"科技ETF", "IWM":"小盘ETF", "DIA":"道指ETF", "XLF":"金融ETF", "XLE":"能源ETF", "XLK":"科技ETF", "XLV":"医疗ETF", "XLI":"工业ETF",
    "TSM":"半导体", "PANW":"网安", "CRWD":"网安", "FTNT":"网安", "ZS":"网安",
    "PLTR":"大数据", "SOUN":"AI",
    "WDAY":"云计算", "TEAM":"企服",
    "KO":"消费", "PEP":"消费", "PM":"消费", "EL":"消费", "YUM":"消费", "MDLZ":"消费",
    "TJX":"零售", "ROST":"零售", "ORLY":"零售", "AZO":"零售", "TSCO":"零售",
    "ISRG":"医疗设备", "MDT":"医疗设备", "BSX":"医疗设备", "SYK":"医疗设备", "ZTS":"医疗",
    "BRK-B":"保险", "ALL":"保险", "MET":"保险", "PRU":"保险",
    "CARR":"工业", "OTIS":"工业", "PWR":"工业", "CMI":"工业", "ITW":"工业",
    "DAL":"航空", "UAL":"航空", "LUV":"航空",
    "ENPH":"新能源", "FSLR":"新能源", "NEE":"电力",
    "EA":"游戏", "TTWO":"游戏", "ROKU":"流媒体",
    "FDX":"物流", "UPS":"物流",
    "TMUS":"电信",
    "HOOD":"金融科技", "SOFI":"金融科技", "AFRM":"金融科技",
    "BILI":"互联网", "TCOM":"旅游",
    "SONY":"消费电子", "CVS":"医药零售",
    "VTI":"大盘ETF", "TLT":"国债ETF", "GLD":"商品ETF", "SLV":"商品ETF", "KWEB":"中概ETF",
}

# 中文名映射
CN_NAME_MAP = {
    "AAPL":"苹果", "MSFT":"微软", "GOOGL":"谷歌", "AMZN":"亚马逊", "META":"Meta", "NVDA":"英伟达", "TSLA":"特斯拉",
    "AMD":"超微半导体", "INTC":"英特尔", "QCOM":"高通", "AVGO":"博通", "ASML":"阿斯麦", "MU":"美光", "SMCI":"超微电脑",
    "IBM":"IBM", "CRM":"赛富时", "ORCL":"甲骨文", "ADBE":"Adobe", "NOW":"ServiceNow",
    "UBER":"优步", "PYPL":"PayPal", "SQ":"Block", "SHOP":"Shopify", "DDOG":"Datadog",
    "BABA":"阿里巴巴", "PDD":"拼多多", "JD":"京东", "NIO":"蔚来", "LI":"理想", "XPEV":"小鹏",
    "COIN":"Coinbase", "MARA":"MARA Holdings", "MSTR":"微策略",
    "IBRX":"ImmunityBio", "NVAX":"诺瓦瓦克斯", "CHWY":"Chewy",
    "JPM":"摩根大通", "GS":"高盛", "MS":"摩根士丹利", "BAC":"美国银行", "V":"Visa", "MA":"万事达",
    "WMT":"沃尔玛", "COST":"好市多", "HD":"家得宝", "CHWY":"Chewy",
    "DIS":"迪士尼", "NFLX":"奈飞", "SPOT":"Spotify",
    "XOM":"埃克森美孚", "CVX":"雪佛龙", "CAT":"卡特彼勒", "BA":"波音", "GE":"通用电气",
    "MELI":"MercadoLibre", "SE":"Sea Limited", "RDDT":"Reddit", "ARM":"ARM Holdings",
    "LLY":"礼来", "UNH":"联合健康", "ABBV":"艾伯维", "JNJ":"强生",
    "TSM":"台积电", "PANW":"Palo Alto", "CRWD":"CrowdStrike", "FTNT":"飞塔", "ZS":"Zscaler",
    "PLTR":"Palantir", "SOUN":"SoundHound",
    "WDAY":"Workday", "TEAM":"Atlassian",
    "KO":"可口可乐", "PEP":"百事", "PM":"菲利普莫里斯", "EL":"雅诗兰黛", "YUM":"百胜", "MDLZ":"亿滋",
    "TJX":"TJX", "ROST":"Ross", "ORLY":"O'Reilly", "AZO":"AutoZone", "TSCO":"Tractor Supply",
    "ISRG":"直觉外科", "MDT":"美敦力", "BSX":"波士顿科学", "SYK":"史赛克", "ZTS":"硕腾",
    "BRK-B":"伯克希尔", "ALL":"好事达", "MET":"大都会", "PRU":"保德信",
    "CARR":"开利", "OTIS":"奥的斯", "PWR":"Quanta", "CMI":"康明斯", "ITW":"伊利诺伊工具",
    "DAL":"达美航空", "UAL":"美联航", "LUV":"西南航空",
    "ENPH":"Enphase", "FSLR":"First Solar", "NEE":"新纪元能源",
    "EA":"艺电", "TTWO":"Take-Two", "ROKU":"Roku",
    "FDX":"联邦快递", "UPS":"UPS",
    "TMUS":"T-Mobile",
    "HOOD":"Robinhood", "SOFI":"SoFi", "AFRM":"Affirm",
    "BILI":"哔哩哔哩", "TCOM":"携程",
    "SONY":"索尼", "CVS":"西维斯",
    "VTI":"全市场ETF", "TLT":"国债ETF", "GLD":"黄金ETF", "SLV":"白银ETF", "KWEB":"中概ETF",
}


def score_from_data(ticker_str, last_price, prev_close, open_price, volume,
                    hist_close, hist_high, hist_low, hist_volume, market_cap=0,
                    high_52w=None, low_52w=None):
    """评分引擎：从预取数据计算技术指标并评分
    与 compute_indicators 共享完全相同的评分逻辑
    """
    if not last_price or not prev_close:
        return None

    change = last_price - prev_close
    change_pct = round((change / prev_close) * 100, 2)
    sector = SECTOR_MAP.get(ticker_str, "其他")
    cn_name = CN_NAME_MAP.get(ticker_str, ticker_str)

    ma5 = hist_close.rolling(5).mean().iloc[-1] if len(hist_close) >= 5 else hist_close.iloc[-1]
    ma10 = hist_close.rolling(10).mean().iloc[-1] if len(hist_close) >= 10 else hist_close.iloc[-1]
    ma20 = hist_close.rolling(20).mean().iloc[-1] if len(hist_close) >= 20 else hist_close.iloc[-1]
    ma50 = hist_close.rolling(50).mean().iloc[-1] if len(hist_close) >= 50 else hist_close.iloc[-1]
    ma200 = hist_close.rolling(200).mean().iloc[-1] if len(hist_close) >= 200 else None

    boll_sma = hist_close.rolling(20).mean()
    boll_std = hist_close.rolling(20).std()
    boll_up = (boll_sma + 2 * boll_std).iloc[-1]
    boll_mid = boll_sma.iloc[-1]
    boll_dn = (boll_sma - 2 * boll_std).iloc[-1]
    boll_pos = (last_price - boll_dn) / (boll_up - boll_dn) if (boll_up - boll_dn) > 0 else 0.5

    last_5 = hist_close.tail(5).values
    last_5_high = hist_high.tail(5).values
    last_5_low = hist_low.tail(5).values
    candle_pattern = _detect_candle_pattern(last_5, last_5_high, last_5_low)

    rsi = _calc_rsi(hist_close, 14)
    macd, macd_signal, macd_hist = _calc_macd(hist_close)
    macd_val = float(macd.iloc[-1])
    macd_sig_val = float(macd_signal.iloc[-1])
    macd_bullish = macd_val > macd_sig_val
    macd_prev_diff = float((macd.shift(1) - macd_signal.shift(1)).iloc[-1])
    macd_curr_diff = macd_val - macd_sig_val
    macd_cross = "bullish_cross" if (macd_curr_diff > 0 and macd_prev_diff < 0) else \
                 "bearish_cross" if (macd_curr_diff < 0 and macd_prev_diff > 0) else "holding"

    avg_vol_20 = hist_volume.tail(20).mean()
    vol_ratio = (volume / avg_vol_20) if avg_vol_20 > 0 else 1.0
    vol_trend = "放量" if vol_ratio > 1.5 else "缩量" if vol_ratio < 0.7 else "正常"

    ma20_deviation = ((last_price - ma20) / ma20) * 100 if ma20 else 0

    if high_52w is None:
        high_52w = float(hist_close.max())
    if low_52w is None:
        low_52w = float(hist_close.min())
    pos_52w = (last_price - low_52w) / (high_52w - low_52w) if (high_52w - low_52w) > 0 else 0.5

    # --- 评分 ---
    bullish_signals = []
    bearish_signals = []
    details = []

    if last_price > ma5 > ma10 and ma5 > ma20:
        bullish_signals.append("均线多头排列")
        details.append({"signal": "📈 均线多头排列", "reason": f"价>{ma5:.1f}>{ma10:.1f}>{ma20:.1f}，主升浪结构完好（短线交易大师：趋势是你的朋友）"})
    if last_price > ma20:
        bullish_signals.append("站上20日均线")
        details.append({"signal": "📊 站上20日均线", "reason": f"现价${last_price:.2f} > MA20${ma20:.2f}，中期趋势偏多（股票K线炼金术：均线是股价的生命线）"})
    if last_price > boll_mid:
        bullish_signals.append("布林中轨上方")
        details.append({"signal": "📉 布林中轨上方", "reason": "价格运行于布林带强势区域，多头控盘（股票K线炼金术：布林通道定多空）"})
    if 40 < rsi < 65:
        bullish_signals.append("RSI健康区间")
        details.append({"signal": "📊 RSI健康区间", "reason": f"RSI({rsi:.0f})处于40-65健康区间，既不过热也不过冷，有上涨空间（同花顺：RSI在40-60时趋势延续性最强）"})
    if macd_bullish:
        bullish_signals.append("MACD多头")
        details.append({"signal": "📈 MACD多头排列", "reason": f"MACD线({macd.iloc[-1]:.2f})位于信号线({macd_signal.iloc[-1]:.2f})上方（同花顺技术分析：MACD多头=中期反弹趋势）"})
    if macd_cross == "bullish_cross":
        bullish_signals.append("MACD金叉")
        details.append({"signal": "⚡ MACD金叉", "reason": "MACD刚刚金叉信号线，是极其强烈的短线爆发信号（短线狙击手：金叉即扣扳机）"})
    if change_pct > 1.0 and vol_ratio > 1.3:
        bullish_signals.append("价涨量增")
        details.append({"signal": "🔥 价涨量增", "reason": f"涨幅{change_pct:+.2f}%配合成交量{vol_ratio:.1f}倍均量，主力真实拉升意图明确（同花顺量价分析：量是价的先行指标）"})
    if candle_pattern in ["bullish_engulfing", "hammer", "morning_star", "piercing"]:
        bullish_signals.append(f"K线多头形态:{candle_pattern}")
        dt = {"bullish_engulfing": "阳包阴吞没形态，空头被彻底击溃（股票K线炼金术：吞没形态是反转最强信号）",
              "hammer": "锤子线探底回升，下方有强支撑（股票K线炼金术：锤子线=空头无力打压）",
              "morning_star": "早晨之星反转形态，趋势逆转信号（股票K线炼金术：启明星照多头至）",
              "piercing": "刺透形态，空头防线被突破（股票K线炼金术：刺透=空翻多标志）"}
        details.append({"signal": f"🕯️ {candle_pattern}", "reason": dt.get(candle_pattern, "多头K线形态")})
    if last_price > ma20 and ma20_deviation < 5:
        bullish_signals.append("回调至均线附近")
        details.append({"signal": "🎯 乖离率适中", "reason": f"现价仅高于MA20{ma20_deviation:+.2f}%，没有过度偏离，适合狙击入场（短线狙击手：回踩均线是经典入场点）"})
    if last_price > ma20 and vol_ratio < 0.8:
        bullish_signals.append("缩量回调清洗浮筹")
        details.append({"signal": "🧹 缩量回调", "reason": f"缩量（{vol_ratio:.1f}倍均量）回踩，主力洗盘吸筹特征明显（盘口：看盘功力决定输赢）"})

    if last_price < ma5 < ma10 and ma5 < ma20:
        bearish_signals.append("均线空头排列")
        details.append({"signal": "📉 均线空头排列", "reason": f"价<{ma5:.1f}<{ma10:.1f}<{ma20:.1f}，下跌趋势确立（短线交易大师：逆势交易是亏损根源）"})
    if last_price < ma20:
        bearish_signals.append("跌破20日均线")
        details.append({"signal": "⚠️ 跌破20日均线", "reason": f"现价${last_price:.2f} < MA20${ma20:.2f}，中期趋势转空（股票K线炼金术：跌破均线=防守位失守）"})
    if rsi > 70:
        bearish_signals.append("RSI超买")
        details.append({"signal": "⚠️ RSI超买", "reason": f"RSI({rsi:.0f})>70，进入超买区，短期回调风险增大（同花顺：超买区不宜追高）"})
    if rsi < 30:
        bearish_signals.append("RSI超卖但趋势向下")
        details.append({"signal": "📉 RSI超卖", "reason": f"RSI({rsi:.0f})<30进入超卖区，但若均线空头排列则不可抄底（短线狙击手：下跌趋势中不猜底）"})
    if not macd_bullish:
        bearish_signals.append("MACD空头")
        details.append({"signal": "📉 MACD空头排列", "reason": f"MACD线({macd.iloc[-1]:.2f})位于信号线下方（同花顺：MACD空头=中期调整趋势）"})
    if macd_cross == "bearish_cross":
        bearish_signals.append("MACD死叉")
        details.append({"signal": "💀 MACD死叉", "reason": "MACD死叉信号线，强烈卖出信号（短线狙击手：死叉即撤离）"})
    if change_pct < -1.5 and vol_ratio > 1.3:
        bearish_signals.append("放量下跌")
        details.append({"signal": "💧 放量下跌", "reason": f"跌幅{change_pct:+.2f}%配合{vol_ratio:.1f}倍均量，主力出货迹象明显（同花顺量价分析：放量下跌=主力不计成本出逃）"})
    if candle_pattern in ["bearish_engulfing", "shooting_star", "evening_star", "hanging_man"]:
        bearish_signals.append(f"K线空头形态:{candle_pattern}")
        dt = {"bearish_engulfing": "阴包阳吞没形态，多头反攻彻底失败（股票K线炼金术：乌云盖顶必须离场）",
              "shooting_star": "射击之星冲高回落，上方抛压极重（股票K线炼金术：十字星不追高）",
              "evening_star": "黄昏之星见顶反转形态（股票K线炼金术：三只乌鸦站枝头）",
              "hanging_man": "上吊线高位放量滞涨（股票K线炼金术：吊颈线=多头最后的挣扎）"}
        details.append({"signal": f"🕯️ {candle_pattern}", "reason": dt.get(candle_pattern, "空头K线形态")})
    if last_price > ma20 and ma20_deviation > 8:
        bearish_signals.append("乖离率过大")
        details.append({"signal": "⚠️ 乖离率过大", "reason": f"现价高于MA20达{ma20_deviation:+.1f}%，短期有回踩需求（短线狙击手：远离均线的票不追）"})
    if change_pct < 0.5 and change_pct > -0.5 and vol_ratio > 1.8 and boll_pos > 0.8:
        bearish_signals.append("高位放量滞涨")
        details.append({"signal": "⚠️ 高位放量滞涨", "reason": f"布林带上轨附近放量（{vol_ratio:.1f}倍）却不涨，主力对倒出货嫌疑（盘口：看盘功力决定输赢）"})

    bullish_score = min(len(bullish_signals) * 10 + (rsi / 14 if rsi > 30 else 0), 100)
    bearish_score = min(len(bearish_signals) * 10 + ((100 - rsi) / 14 if rsi < 70 else 0), 100)
    if change_pct > 2:
        bullish_score *= 1.15
    elif change_pct < -2:
        bearish_score *= 1.15
    if market_cap and market_cap < 2_000_000_000:
        bullish_score *= 1.1
        bearish_score *= 1.1

    bullish_score = round(min(bullish_score, 100), 0)
    bearish_score = round(min(bearish_score, 100), 0)
    direction = "buy" if bullish_score >= bearish_score else "sell"

    return {
        "ticker": ticker_str,
        "name": cn_name,
        "sector": sector,
        "price": round(last_price, 2),
        "change": round(change, 2),
        "change_pct": change_pct,
        "volume": int(volume),
        "market_cap": market_cap,
        "ma5": round(ma5, 2),
        "ma10": round(ma10, 2),
        "ma20": round(ma20, 2),
        "ma50": round(ma50, 2),
        "ma200": round(ma200, 2) if ma200 else None,
        "boll_up": round(boll_up, 2),
        "boll_mid": round(boll_mid, 2),
        "boll_dn": round(boll_dn, 2),
        "boll_pos": round(boll_pos, 3),
        "rsi": round(rsi, 1),
        "macd": round(float(macd.iloc[-1]), 4),
        "macd_signal": round(float(macd_signal.iloc[-1]), 4),
        "macd_bullish": bool(macd_bullish),
        "macd_cross": macd_cross,
        "vol_ratio": round(vol_ratio, 2),
        "vol_trend": vol_trend,
        "avg_vol_20": int(avg_vol_20) if not pd.isna(avg_vol_20) else int(volume),
        "ma20_deviation": round(ma20_deviation, 2),
        "pos_52w": round(pos_52w, 3),
        "high_52w": round(float(high_52w), 2) if high_52w else None,
        "low_52w": round(float(low_52w), 2) if low_52w else None,
        "candle_pattern": candle_pattern,
        "bullish_score": int(bullish_score),
        "bearish_score": int(bearish_score),
        "direction": direction,
        "bullish_signals": bullish_signals,
        "bearish_signals": bearish_signals,
        "details": details,
        "analysis_time": datetime.now().isoformat(),
        "data_source": "tradingview",
    }


def compute_indicators(ticker_str: str) -> dict:
    """原有 yfinance 版本 — 单只股票分析入口"""
    try:
        t = yf.Ticker(ticker_str)
        info = t.info
        fast = t.fast_info
        last_price = float(fast.get("lastPrice", 0))
        prev_close = info.get("previousClose", 0)
        if not last_price or not prev_close:
            return None
        day_high = info.get("dayHigh", last_price)
        day_low = info.get("dayLow", last_price)
        open_price = info.get("open", prev_close)
        volume = fast.get("lastVolume", 0) or 0
        market_cap = info.get("marketCap", 0)
        high_52w = info.get("fiftyTwoWeekHigh")
        low_52w = info.get("fiftyTwoWeekLow")

        hist = t.history(period="6mo")
        if hist.empty or len(hist) < 20:
            hist = t.history(period="1mo")
            if hist.empty or len(hist) < 10:
                return None

        return score_from_data(
            ticker_str, last_price, prev_close, open_price, volume,
            hist["Close"].astype(float), hist["High"].astype(float),
            hist["Low"].astype(float), hist["Volume"].astype(float),
            market_cap=market_cap, high_52w=high_52w, low_52w=low_52w,
        )
    except Exception as e:
        print(f"Error processing {ticker_str}: {e}")
        return None


def fetch_all_tv() -> dict:
    """
    全量扫描：TradingView WebSocket 实时行情 + yfinance 批量历史数据
    纯Python，无需Node.js，无限速

    策略：
    1. yfinance.download() 大批量获取历史OHLCV（~15秒）
    2. TradingView WebSocket 获取实时价、涨跌幅（~10-15秒）
    3. 合并数据并使用现有评分引擎
    """
    import json

    all_tickers = SCAN_UNIVERSE
    results = []
    ok_count = 0

    # ---- Step 1: yfinance 批量历史数据 ----
    # 分批下载避免 Rendder 512MB OOM
    hist_data = {}
    batch_size = 30
    for i in range(0, len(all_tickers), batch_size):
        batch = all_tickers[i:i + batch_size]
        try:
            b = yf.download(batch, period="1mo", progress=False, group_by="ticker")
            if b is not None and not b.empty:
                if isinstance(b.columns, pd.MultiIndex):
                    for t in b.columns.get_level_values(0).unique():
                        try:
                            td = b[t]
                            close = td.get("Close", pd.Series(dtype=float)).dropna().astype(float)
                            if len(close) < 5:
                                continue
                            high = td.get("High", pd.Series(dtype=float)).dropna().astype(float)
                            low = td.get("Low", pd.Series(dtype=float)).dropna().astype(float)
                            vol = td.get("Volume", pd.Series(dtype=float)).dropna().astype(float)
                            hist_data[t] = {"close": close, "high": high, "low": low, "volume": vol}
                        except Exception:
                            continue
            print(f"  历史批次 {i//batch_size+1}/{(len(all_tickers)+batch_size-1)//batch_size}: {len(batch)}只 → {len([t for t in batch if t in hist_data])}成功")
        except Exception as e:
            print(f"  批次 {i//batch_size+1} 失败: {e}")
    print(f"  历史总计: {len(hist_data)}/{len(all_tickers)}")

    # ---- Step 2: 实时行情 ----
    # 策略: HTTP 并行抓取 (快且稳定, 180只~12s) 优先, WebSocket 补漏
    realtime = {}
    try:
        from tv_ws_client import fetch_realtime_prices, fetch_realtime_http
        # HTTP 并行抓取全量 — 更高worker数, 更大超时
        http_timeout = max(30, min(60, len(all_tickers) * 1.5))
        realtime = fetch_realtime_http(all_tickers, timeout=http_timeout)
        print(f"  HTTP 实时: {len(realtime)}/{len(all_tickers)}")
    except Exception as e:
        print(f"  HTTP failed: {e}")

    # WS 补漏 — 只查 HTTP 没覆盖到的
    if len(realtime) < len(all_tickers) * 0.85:
        missing = [t for t in all_tickers if t not in realtime]
        if missing:
            try:
                ws_supplement = fetch_realtime_prices(missing, timeout=25)
                print(f"  WS 补充: {len(ws_supplement)}/{len(missing)}")
                realtime.update(ws_supplement)
            except Exception as e:
                print(f"  WS supplement: {e}")

    # ---- Step 3: 合并数据并评分 ----
    for tkr in all_tickers:
        try:
            rt = realtime.get(tkr)
            if not rt:
                continue

            last_price = rt["price"]
            change_pct = rt["change_pct"]
            change = rt["change"]
            volume = rt["volume"]

            if not last_price or last_price <= 0:
                continue

            prev_close = last_price - (last_price * change_pct / 100) if change_pct else last_price * 0.995
            open_price = prev_close

            hist = hist_data.get(tkr)
            if hist:
                close_s = hist["close"].copy()
                if len(close_s) >= 2:
                    close_s.iloc[-1] = last_price
                r = score_from_data(
                    tkr, last_price, prev_close, open_price, volume,
                    close_s, hist["high"], hist["low"], hist["volume"],
                )
            else:
                sector = SECTOR_MAP.get(tkr, "其他")
                cn_name = CN_NAME_MAP.get(tkr, tkr)
                ma20_val = last_price
                rsi_val = 50.0

                bullish = []
                bearish = []
                details_b = []

                if change_pct > 1.0:
                    bullish.append("实时上涨")
                    details_b.append({"signal": "🔥 实时上涨", "reason": f"实时涨幅{change_pct:+.1f}%动能强劲"})
                if change_pct < -1.0:
                    bearish.append("实时下跌")
                    details_b.append({"signal": "💧 实时下跌", "reason": f"实时跌幅{change_pct:+.1f}%动能弱势"})

                bscore = min(len(bullish) * 10 + 50, 100)
                bscore2 = min(len(bearish) * 10 + 50, 100)
                if change_pct > 2: bscore = min(bscore * 1.15, 100)
                if change_pct < -2: bscore2 = min(bscore2 * 1.15, 100)

                r = {
                    "ticker": tkr, "name": cn_name, "sector": sector,
                    "price": round(last_price, 2), "change": round(change, 2),
                    "change_pct": round(change_pct, 2), "volume": int(volume),
                    "market_cap": 0, "ma5": 0, "ma10": 0,
                    "ma20": round(ma20_val, 2), "ma50": 0, "ma200": None,
                    "boll_up": round(last_price * 1.05, 2), "boll_mid": round(last_price, 2),
                    "boll_dn": round(last_price * 0.95, 2), "boll_pos": 0.5,
                    "rsi": round(rsi_val, 1), "macd": 0, "macd_signal": 0,
                    "macd_bullish": False, "macd_cross": "holding",
                    "vol_ratio": 1.0, "vol_trend": "正常",
                    "avg_vol_20": int(volume), "ma20_deviation": 0,
                    "pos_52w": 0.5, "high_52w": None, "low_52w": None,
                    "candle_pattern": "normal",
                    "bullish_score": int(bscore), "bearish_score": int(bscore2),
                    "direction": "buy" if bscore >= bscore2 else "sell",
                    "bullish_signals": bullish, "bearish_signals": bearish,
                    "details": details_b,
                    "analysis_time": datetime.now().isoformat(),
                    "data_source": "tradingview_ws",
                }

            if r:
                results.append(r)
                ok_count += 1
        except Exception as e:
            continue

    buys = sorted([r for r in results if r["direction"] == "buy"],
                  key=lambda x: x["bullish_score"], reverse=True)[:10]
    sells = sorted([r for r in results if r["direction"] == "sell"],
                   key=lambda x: x["bearish_score"], reverse=True)[:10]

    return {
        "buys": buys,
        "sells": sells,
        "total_scanned": len(results),
        "total_universe": len(SCAN_UNIVERSE),
        "timestamp": datetime.now().isoformat(),
        "data_source": "tradingview_ws",
    }


def _calc_rsi(series: pd.Series, period: int = 14) -> float:
    """计算 RSI"""
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else 50.0


def _calc_macd(series: pd.Series):
    """计算 MACD 指标"""
    exp1 = series.ewm(span=12, adjust=False).mean()
    exp2 = series.ewm(span=26, adjust=False).mean()
    macd = exp1 - exp2
    signal = macd.ewm(span=9, adjust=False).mean()
    hist = macd - signal
    return macd, signal, hist


def _detect_candle_pattern(closes, highs, lows) -> str:
    """K线形态识别 (股票K线炼金术)"""
    if len(closes) < 3:
        return "unknown"

    c1, c2, c3 = closes[-3], closes[-2], closes[-1]
    h1, h2, h3 = highs[-3], highs[-2], highs[-1]
    l1, l2, l3 = lows[-3], lows[-2], lows[-1]
    o1, o2, o3 = closes[-4] if len(closes) >= 4 else c1, c1, c2  # approximate opens

    body1 = abs(c1 - o1)
    body2 = abs(c2 - o2)
    body3 = abs(c3 - o3)
    upper1 = h1 - max(c1, o1)
    lower1 = min(c1, o1) - l1

    # 阳包阴 (Bullish Engulfing)
    if c2 < o2 and c3 > o3 and c3 > h2 and o3 < l2:
        return "bullish_engulfing"

    # 阴包阳 (Bearish Engulfing)
    if c2 > o2 and c3 < o3 and c3 < l2 and o3 > h2:
        return "bearish_engulfing"

    # 锤子线 (Hammer)
    if body3 > 0 and lower1 > 2 * body3 and upper1 < body3 * 0.3:
        return "hammer"

    # 上吊线 (Hanging Man) — 高位锤子线
    if body2 > 0 and lower1 > 2 * body2 and upper1 < body2 * 0.3 and c1 > o1:
        return "hanging_man"

    # 射击之星 (Shooting Star)
    if body3 > 0 and upper1 > 2 * body3 and lower1 < body3 * 0.3:
        return "shooting_star"

    # 启明星 (Morning Star)
    if c2 < o2 and abs(c3 - o3) > abs(c2 - o2) * 0.7 and c3 > max(o2, c2):
        return "morning_star"

    # 黄昏星 (Evening Star)
    if c2 > o2 and abs(c3 - o3) > abs(c2 - o2) * 0.7 and c3 < min(o2, c2):
        return "evening_star"

    # 刺透形态 (Piercing)
    if c2 < o2 and c3 > o3 and o3 < l2 and c3 > (c2 + o2) / 2:
        return "piercing"

    return "normal"


def scan_market(batch_size: int = 20) -> dict:
    """扫描全市场，返回排名结果"""
    results = []
    total = len(SCAN_UNIVERSE)

    for i in range(0, total, batch_size):
        batch = SCAN_UNIVERSE[i:i + batch_size]
        print(f"扫描批次 {i // batch_size + 1}/{(total + batch_size - 1) // batch_size} ({len(batch)} 只)...")
        for ticker in batch:
            result = compute_indicators(ticker)
            if result:
                results.append(result)
            time.sleep(0.3)  # yfinance 限速

    # 分类排名
    buys = sorted([r for r in results if r["direction"] == "buy"], key=lambda x: x["bullish_score"], reverse=True)[:10]
    sells = sorted([r for r in results if r["direction"] == "sell"], key=lambda x: x["bearish_score"], reverse=True)[:10]

    return {
        "buys": buys,
        "sells": sells,
        "total_scanned": len(results),
        "timestamp": datetime.now().isoformat(),
    }


def scan_single(ticker: str) -> dict:
    """扫描单只股票"""
    ticker = ticker.strip().upper()
    result = compute_indicators(ticker)
    if result:
        return {"found": True, "stock": result}
    return {"found": False, "ticker": ticker}


def search_stocks(query: str, max_results: int = 15) -> list:
    """搜索股票 (按名称或代码)"""
    query = query.lower().strip()
    if not query:
        return []

    matches = []
    for ticker in SCAN_UNIVERSE:
        name = CN_NAME_MAP.get(ticker, ticker).lower()
        if query in ticker.lower() or query in name:
            matches.append({"ticker": ticker, "name": CN_NAME_MAP.get(ticker, ticker)})
        if len(matches) >= max_results:
            break

    return matches


# 本地测试
if __name__ == "__main__":
    print("=== 美股扫描引擎测试 ===")
    result = compute_indicators("AAPL")
    if result:
        print(f"苹果: ${result['price']} ({result['change_pct']:+.2f}%)")
        print(f"  多头分: {result['bullish_score']} | 空头分: {result['bearish_score']}")
        print(f"  方向: {'📈做多' if result['direction'] == 'buy' else '📉做空'}")
        print(f"  RSI: {result['rsi']} | MACD: {'多头✓' if result['macd_bullish'] else '空头✗'}")
        print(f"  均线: MA5={result['ma5']} MA20={result['ma20']}")
        print(f"  布林: 上={result['boll_up']} 中={result['boll_mid']} 下={result['boll_dn']}")
        print(f"  信号: {result['details']}")
