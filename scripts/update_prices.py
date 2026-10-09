"""Lấy giá đóng cửa mới nhất cho mọi mã trong data/tickers.json và ghi vào data/prices.json.

Chỉ dùng thư viện chuẩn của Python. Thử lần lượt nhiều nguồn công khai;
nguồn nào trả về dữ liệu hợp lệ trước thì dùng. Không cần API key.

Chạy thử trên máy:  python scripts/update_prices.py
"""
from __future__ import annotations

import json
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
VN_TZ = timezone(timedelta(hours=7))
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


def http_json(url: str, *, data: dict | None = None, headers: dict | None = None, timeout: int = 20):
    h = {"User-Agent": UA, "Accept": "application/json, text/plain, */*"}
    if headers:
        h.update(headers)
    body = None
    if data is not None:
        body = json.dumps(data).encode()
        h["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=h, method="POST" if body else "GET")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def to_date(ts) -> str:
    """Epoch giây hoặc chuỗi ngày -> YYYY-MM-DD (giờ Việt Nam)."""
    if isinstance(ts, (int, float)):
        if ts > 1e12:  # mili giây
            ts /= 1000
        return datetime.fromtimestamp(ts, VN_TZ).strftime("%Y-%m-%d")
    s = str(ts).strip()
    if s.isdigit():
        return to_date(int(s))
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(s[:10], fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return s[:10]


# --- Các nguồn giá. Mỗi hàm trả về danh sách [(ngày, giá_đóng_cửa), ...] cũ -> mới. ---

def src_vci(t: str):
    now = int(time.time())
    res = http_json(
        "https://trading.vietcap.com.vn/api/chart/OHLCChart/gap-chart",
        data={"timeFrame": "ONE_DAY", "symbols": [t], "to": now, "countBack": 10},
        headers={"Referer": "https://trading.vietcap.com.vn/", "Origin": "https://trading.vietcap.com.vn"},
    )
    row = res[0] if isinstance(res, list) else res
    return [(to_date(ts), float(c)) for ts, c in zip(row["t"], row["c"])]


def src_vndirect(t: str):
    since = (datetime.now(VN_TZ) - timedelta(days=20)).strftime("%Y-%m-%d")
    res = http_json(
        f"https://api-finfo.vndirect.com.vn/v4/stock_prices?sort=date&q=code:{t}~date:gte:{since}&size=10&page=1",
        headers={"Referer": "https://dstock.vndirect.com.vn/", "Origin": "https://dstock.vndirect.com.vn"},
    )
    rows = sorted(res["data"], key=lambda r: r["date"])
    return [(r["date"], float(r["close"])) for r in rows]


def src_tcbs(t: str):
    now = int(time.time())
    res = http_json(
        "https://apipubaws.tcbs.com.vn/stock-insight/v2/stock/bars-long-term"
        f"?ticker={t}&type=stock&resolution=D&to={now}&countBack=10"
    )
    return [(to_date(r["tradingDate"]), float(r["close"])) for r in res["data"]]


def src_kbs(t: str):
    end = datetime.now(VN_TZ)
    start = end - timedelta(days=20)
    res = http_json(
        f"https://kbbuddywts.kbsec.com.vn/iis-server/investment/stocks/{t}/data_day"
        f"?sdate={start:%d-%m-%Y}&edate={end:%d-%m-%Y}"
    )
    rows = res.get("data_day") or res.get("data") or []
    out = [(to_date(r.get("t") or r.get("TradingDate")), float(r.get("c") or r.get("ClosePrice"))) for r in rows]
    return sorted(out)


SOURCES = [("VCI", src_vci), ("VNDirect", src_vndirect), ("TCBS", src_tcbs), ("KBS", src_kbs)]


def rescale(price: float, reference: float | None) -> float:
    """Nguồn trả giá theo đồng hoặc nghìn đồng. Chọn đơn vị gần với giá đã biết nhất."""
    if reference and reference > 0:
        return min((price, price * 1000), key=lambda p: abs(p - reference) / reference)
    return price * 1000 if price < 500 else price


def fetch(t: str, reference: float | None):
    errors = []
    for name, fn in SOURCES:
        try:
            rows = [(d, c) for d, c in fn(t) if c and c > 0]
            if not rows:
                raise ValueError("không có dữ liệu")
            rows = rows[-2:]
            last_d, last_c = rows[-1]
            close = rescale(last_c, reference)
            prev = rescale(rows[0][1], close) if len(rows) == 2 else None
            return {"close": round(close), "prevClose": round(prev) if prev else None,
                    "date": last_d, "source": name}, errors
        except Exception as e:  # noqa: BLE001 — thử nguồn tiếp theo
            errors.append(f"{name}: {type(e).__name__}: {str(e)[:120]}")
    return None, errors


def main() -> int:
    tickers = json.loads((DATA / "tickers.json").read_text(encoding="utf-8"))
    prices_path = DATA / "prices.json"
    old = json.loads(prices_path.read_text(encoding="utf-8")) if prices_path.exists() else {"prices": {}}
    prices = old.get("prices", {})

    ok, failed = 0, []
    for t in tickers:
        ref = prices.get(t, {}).get("close")
        if ref is None:
            stock_file = DATA / "stocks" / f"{t}.json"
            if stock_file.exists():
                ref = json.loads(stock_file.read_text(encoding="utf-8")).get("price")
        got, errors = fetch(t, ref)
        if got:
            prices[t] = got
            ok += 1
            print(f"{t}: {got['close']:,} ({got['date']}, nguồn {got['source']})")
        else:
            failed.append(t)
            print(f"{t}: KHÔNG lấy được giá -> " + " | ".join(errors))
        time.sleep(0.5)

    out = {"updatedAt": datetime.now(VN_TZ).isoformat(timespec="seconds"), "prices": prices}
    prices_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Xong: {ok}/{len(tickers)} mã.")
    # Chỉ báo lỗi (để GitHub gửi email) khi không lấy được mã nào.
    return 1 if tickers and ok == 0 else 0


if __name__ == "__main__":
    sys.exit(main())
