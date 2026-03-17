import os
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional

import requests

BASE_URL = "https://api.binance.com"
EXCHANGE_INFO_URL = f"{BASE_URL}/api/v3/exchangeInfo"
KLINES_URL = f"{BASE_URL}/api/v3/klines"
REQUEST_TIMEOUT = 15
RETRY_TIMES = 3
RETRY_SLEEP_SECONDS = 1
KLINE_INTERVAL = "1d"


def request_json(url: str, params: Optional[Dict] = None) -> Optional[Dict]:
    """带基础重试能力的 GET 请求。"""
    for attempt in range(1, RETRY_TIMES + 1):
        try:
            response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            print(f"[警告] 请求失败 {attempt}/{RETRY_TIMES}: {url} params={params}, error={exc}")
            if attempt < RETRY_TIMES:
                time.sleep(RETRY_SLEEP_SECONDS)
    return None


def fetch_usdt_symbols() -> List[Dict]:
    """获取所有 USDT 交易对。"""
    data = request_json(EXCHANGE_INFO_URL)
    if not data or "symbols" not in data:
        return []

    usdt_symbols = []
    for item in data["symbols"]:
        # 仅保留状态正常、且以 USDT 结尾的现货交易对
        if item.get("quoteAsset") == "USDT" and item.get("status") == "TRADING":
            usdt_symbols.append(item)
    return usdt_symbols


def fetch_listing_datetime(symbol: str) -> Optional[datetime]:
    """通过最早 K 线 open_time 推断交易对实际上线时间。"""
    params = {
        "symbol": symbol,
        "interval": KLINE_INTERVAL,
        "startTime": 0,
        "limit": 1,
    }
    data = request_json(KLINES_URL, params=params)

    # 返回数据格式示例: [[open_time, open, high, low, close, volume, ...]]
    if not isinstance(data, list) or not data or not isinstance(data[0], list):
        return None

    open_time_ms = data[0][0]
    if not isinstance(open_time_ms, int):
        return None

    return datetime.fromtimestamp(open_time_ms / 1000, tz=timezone.utc)


def format_markdown(rows: List[Dict]) -> str:
    """把筛选结果整理为 Markdown 表格。"""
    if not rows:
        return "## Binance 上线时间筛选结果\n\n最近 30~365 天内暂无符合条件的 USDT 交易对。"

    lines = [
        "## Binance 上线时间筛选结果",
        "",
        "| 币种名称 | 上线日期(UTC) | 存续天数 |",
        "|---|---|---|",
    ]

    for row in rows:
        lines.append(f"| {row['symbol']} | {row['listing_date']} | {row['age_days']} |")

    return "\n".join(lines)


def main() -> None:
    now = datetime.now(timezone.utc)
    min_days = 30
    max_days = 365

    symbols = fetch_usdt_symbols()
    if not symbols:
        markdown = "## Binance 上线时间筛选结果\n\n获取交易对失败或无可用数据。"
        print(markdown)
        return

    rows = []
    for item in symbols:
        symbol = item.get("symbol")
        if not symbol:
            continue

        listing_dt = fetch_listing_datetime(symbol)
        # 为避免触发接口限频，增加轻量延迟
        time.sleep(0.05)

        if not listing_dt:
            continue

        age_days = (now - listing_dt).days
        if min_days <= age_days <= max_days:
            rows.append(
                {
                    "symbol": symbol,
                    "listing_date": listing_dt.strftime("%Y-%m-%d"),
                    "age_days": age_days,
                }
            )

    rows.sort(key=lambda x: x["age_days"])
    markdown = format_markdown(rows)
    print(markdown)

    # 兼容直接运行时写入 GitHub Step Summary
    summary_path = os.getenv("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as f:
            f.write(markdown + "\n")


if __name__ == "__main__":
    main()
