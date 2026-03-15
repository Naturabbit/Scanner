diff --git a/scanner.py b/scanner.py
index 8b137891791fe96927ad78e64b0aad7bded08bdc..24597941c60e60551caffa739539e840fe4525ba 100644
--- a/scanner.py
+++ b/scanner.py
@@ -1 +1,139 @@
+#!/usr/bin/env python3
+"""Scan active Polymarket markets and print links for ultra-low priced outcomes."""
 
+from __future__ import annotations
+
+import json
+import sys
+import urllib.error
+import urllib.parse
+import urllib.request
+from typing import Any, Iterable
+
+API_URL = "https://gamma-api.polymarket.com/markets"
+PAGE_SIZE = 100
+LOWER_BOUND = 0.0
+UPPER_BOUND = 0.0011
+TIMEOUT = 20
+
+
+def parse_prices(raw_prices: Any) -> list[float]:
+    """Normalize `outcomePrices` into a list of floats."""
+    if raw_prices is None:
+        return []
+
+    parsed = raw_prices
+    if isinstance(raw_prices, str):
+        text = raw_prices.strip()
+        if not text:
+            return []
+        try:
+            parsed = json.loads(text)
+        except json.JSONDecodeError:
+            parsed = [p.strip() for p in text.split(",") if p.strip()]
+
+    if not isinstance(parsed, Iterable) or isinstance(parsed, (str, bytes, dict)):
+        return []
+
+    prices: list[float] = []
+    for item in parsed:
+        try:
+            prices.append(float(item))
+        except (TypeError, ValueError):
+            continue
+    return prices
+
+
+def price_in_target_range(prices: Iterable[float]) -> bool:
+    return any(LOWER_BOUND <= price <= UPPER_BOUND for price in prices)
+
+
+def http_get_json(url: str, params: dict[str, Any]) -> Any:
+    query = urllib.parse.urlencode(params)
+    request_url = f"{url}?{query}"
+    request = urllib.request.Request(
+        request_url,
+        headers={
+            "Accept": "application/json",
+            "User-Agent": "scanner/1.0",
+        },
+    )
+    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
+        charset = response.headers.get_content_charset("utf-8")
+        body = response.read().decode(charset)
+    return json.loads(body)
+
+
+def fetch_page(offset: int) -> list[dict[str, Any]]:
+    params = {
+        "active": "true",
+        "closed": "false",
+        "limit": PAGE_SIZE,
+        "offset": offset,
+    }
+
+    payload = http_get_json(API_URL, params)
+    if isinstance(payload, list):
+        return payload
+    if isinstance(payload, dict):
+        for key in ("data", "markets", "results"):
+            value = payload.get(key)
+            if isinstance(value, list):
+                return value
+    return []
+
+
+def scan_markets() -> list[str]:
+    matched_links: list[str] = []
+    offset = 0
+    total_scanned = 0
+    page = 1
+
+    while True:
+        markets = fetch_page(offset)
+        if not markets:
+            print(f"[进度] 第 {page} 页无数据，扫描结束。")
+            break
+
+        print(f"[进度] 正在扫描第 {page} 页，{len(markets)} 个标的（offset={offset}）...")
+
+        for market in markets:
+            total_scanned += 1
+            slug = market.get("slug")
+            prices = parse_prices(market.get("outcomePrices"))
+            if slug and price_in_target_range(prices):
+                link = f"https://polymarket.com/market/{slug}"
+                matched_links.append(link)
+                print(f"[发现] {link} | outcomePrices={prices}")
+
+        if len(markets) < PAGE_SIZE:
+            print("[进度] 已到最后一页。")
+            break
+
+        offset += PAGE_SIZE
+        page += 1
+
+    print(f"\n[完成] 共扫描 {total_scanned} 个 active=true 标的。")
+    print(f"[完成] 命中 {len(matched_links)} 个标的。")
+    if matched_links:
+        print("\n[结果链接]")
+        for link in matched_links:
+            print(link)
+
+    return matched_links
+
+
+def main() -> int:
+    try:
+        scan_markets()
+        return 0
+    except urllib.error.URLError as exc:
+        print(f"[错误] 网络请求失败: {exc}", file=sys.stderr)
+        return 1
+    except json.JSONDecodeError as exc:
+        print(f"[错误] 解析响应 JSON 失败: {exc}", file=sys.stderr)
+        return 1
+
+
+if __name__ == "__main__":
+    raise SystemExit(main())
