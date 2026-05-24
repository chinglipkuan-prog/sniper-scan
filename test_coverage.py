#!/usr/bin/env python3
"""Test real-time data coverage for all 181 stocks"""
from tv_ws_client import fetch_realtime_prices, fetch_realtime_http
from scanner import SCAN_UNIVERSE
import time
import sys

print(f"Testing coverage for {len(SCAN_UNIVERSE)} stocks")

# Test HTTP real-time (primary)
t0 = time.time()
http_data = fetch_realtime_http(SCAN_UNIVERSE, timeout=40)
t1 = time.time()
print(f"HTTP实时: {len(http_data)}/{len(SCAN_UNIVERSE)}, {t1-t0:.1f}s")

# Test WebSocket real-time 
t0 = time.time()
ws_data = fetch_realtime_prices(SCAN_UNIVERSE, timeout=40)
t1 = time.time()
print(f"WS实时: {len(ws_data)}/{len(SCAN_UNIVERSE)}, {t1-t0:.1f}s")

# Check overlap
http_set = set(http_data.keys())
ws_set = set(ws_data.keys())
print(f"HTTP独有: {len(http_set - ws_set)}")
print(f"WS独有: {len(ws_set - http_set)}")
print(f"交集: {len(http_set & ws_set)}")
print(f"合并: {len(http_set | ws_set)}")

# Missing stocks
all_t = set(SCAN_UNIVERSE)
http_only = http_set - ws_set
ws_only = ws_set - http_set
missing = all_t - (http_set | ws_set)
print(f"HTTP独有股票: {sorted(http_only)[:10]}...")
print(f"WS独有股票: {sorted(ws_only)[:10]}...")
print(f"全部缺失: {len(missing)} - {sorted(missing)}")

# Save for scanner optimization
print(f"\nSCAN_OPTIMIZATION:")
print(f"Use HTTP as primary: {len(http_data)} stocks available")
print(f"Use WS as supplement: {len(ws_data)} stocks available")
