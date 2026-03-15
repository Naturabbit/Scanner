import time
import requests

API_URL = "https://gamma-api.polymarket.com/markets"
PAGE_SIZE = 100
MIN_PRICE = 0.0
MAX_PRICE = 0.0011
TIMEOUT = 20
RETRY_TIMES = 3


def parse_outcome_prices(raw_prices):
    """把 outcomePrices 解析成 float 列表。"""
    if raw_prices is None:
        return []

    if isinstance(raw_prices, list):
        items = raw_prices
    elif isinstance(raw_prices, str):
        text = raw_prices.strip()
        if not text:
            return []
        # 兼容类似 "[0.1,0.9]" 或 "0.1,0.9"
        text = text.strip("[]")
        items = [part.strip().strip('"').strip("'") for part in text.split(",") if part.strip()]
    else:
        return []

    prices = []
    for item in items:
        try:
            prices.append(float(item))
        except (TypeError, ValueError):
            continue
    return prices


def is_target_market(prices):
    return any(MIN_PRICE <= price <= MAX_PRICE for price in prices)


def fetch_markets_page(offset):
    params = {
        "active": "true",
        "closed": "false",
        "limit": PAGE_SIZE,
        "offset": offset,
    }

    for attempt in range(1, RETRY_TIMES + 1):
        try:
            print("正在尝试连接 Polymarket API...")
            response = requests.get(API_URL, params=params, timeout=TIMEOUT)
            response.raise_for_status()
            data = response.json()

            if isinstance(data, list):
                return data
            if isinstance(data, dict):
                for key in ("data", "markets", "results"):
                    value = data.get(key)
                    if isinstance(value, list):
                        return value
            return []
        except requests.RequestException as exc:
            print(f"[警告] 第 {attempt}/{RETRY_TIMES} 次请求失败: {exc}")
            if attempt < RETRY_TIMES:
                time.sleep(2)

    print("[错误] 多次请求失败，本次扫描提前结束。")
    return []


def scan_markets():
    matched_links = []
    total_scanned = 0
    page = 1
    offset = 0

    while True:
        markets = fetch_markets_page(offset)
        if not markets:
            print(f"[进度] 第 {page} 页无数据或请求失败，扫描结束。")
            break

        print(f"[进度] 正在扫描第 {page} 页，{len(markets)} 个标的（offset={offset}）")

        for market in markets:
            total_scanned += 1
            slug = market.get("slug")
            prices = parse_outcome_prices(market.get("outcomePrices"))

            if slug and is_target_market(prices):
                link = f"https://polymarket.com/market/{slug}"
                matched_links.append(link)
                print(f"[发现] {link} | outcomePrices={prices}")

        if len(markets) < PAGE_SIZE:
            print("[进度] 已到最后一页。")
            break

        offset += PAGE_SIZE
        page += 1
        time.sleep(0.2)

    print(f"\n[完成] 共扫描 {total_scanned} 个 active=true 标的。")
    print(f"[完成] 命中 {len(matched_links)} 个标的。")

    if matched_links:
        print("\n[结果链接]")
        for link in matched_links:
            print(link)


if __name__ == "__main__":
    scan_markets()
