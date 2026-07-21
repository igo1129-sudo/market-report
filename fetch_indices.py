#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_indices.py
每天自动抓取全球主要股指收盘价及涨跌幅，生成 report.html。
数据源：Yahoo Finance（通过 yfinance 库），免费公开数据，一般有几分钟延迟。

用法：
    python fetch_indices.py

输出：
    report.html   —— 网页报告（样式仿照原截图，红涨绿跌）
    indices.json  —— 原始数据快照，便于排查数据问题或二次使用
"""

import json
import sys
from datetime import datetime, timezone, timedelta

import yfinance as yf

# ---------------------------------------------------------------------------
# 指数清单：(显示名称, Yahoo Finance 代码)
# 分组对应原截图中的四个区块
# ---------------------------------------------------------------------------
GROUPS = [
    {
        "title": "欧美主要指数",
        "bg": "#d9e6d3",
        "indices": [
            ("道琼斯工业", "^DJI"),
            ("标普500", "^GSPC"),
            ("纳斯达克综指", "^IXIC"),
            ("法国CAC40", "^FCHI"),
            ("德国DAX", "^GDAXI"),
            ("英国富时100", "^FTSE"),
        ],
    },
    {
        "title": "新加坡",
        "bg": "#f6ded0",
        "indices": [
            ("新加坡海峡指数", "^STI"),
        ],
    },
    {
        "title": "港股",
        "bg": "#f6ded0",
        "indices": [
            ("恒生指数", "^HSI"),
            ("恒生国企", "^HSCE"),
            ("恒生科技", "HSTECH.HK"),
        ],
    },
    {
        "title": "A股",
        "bg": "#d9e6d3",
        "indices": [
            ("上证指数", "000001.SS"),
            ("深证成指", "399001.SZ"),
            ("沪深300", "000300.SS"),
            ("中证500", "000905.SS"),
            ("创业板指", "399006.SZ"),
            ("科创50", "000688.SS"),
        ],
    },
]

# 数值格式化：指数点位是否显示小数
NO_DECIMAL = {"^DJI", "^GSPC", "^IXIC", "^FCHI", "^GDAXI", "^FTSE", "^STI",
              "^HSI", "^HSCE", "HSTECH.HK", "000001.SS", "399001.SZ",
              "000300.SS", "000905.SS", "399006.SZ", "000688.SS"}


def fetch_one(ticker: str):
    """返回 (最新收盘价, 涨跌幅%, 是否成功, 错误信息)"""
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period="5d", interval="1d")
        if hist.empty or len(hist) < 2:
            return None, None, False, "历史数据不足（可能是节假日或代码错误）"
        last_close = hist["Close"].iloc[-1]
        prev_close = hist["Close"].iloc[-2]
        pct = (last_close - prev_close) / prev_close * 100
        return float(last_close), float(pct), True, None
    except Exception as e:
        return None, None, False, str(e)


def fmt_value(ticker: str, value: float) -> str:
    if ticker in NO_DECIMAL:
        return f"{value:,.0f}"
    return f"{value:,.2f}"


def build_report():
    results = []
    errors = []
    for group in GROUPS:
        g = {"title": group["title"], "bg": group["bg"], "items": []}
        for name, ticker in group["indices"]:
            value, pct, ok, err = fetch_one(ticker)
            if ok:
                g["items"].append({
                    "name": name, "ticker": ticker,
                    "value": fmt_value(ticker, value), "pct": pct,
                })
            else:
                g["items"].append({
                    "name": name, "ticker": ticker,
                    "value": "N/A", "pct": None,
                })
                errors.append(f"{name} ({ticker}): {err}")
        results.append(g)
    return results, errors


def render_html(groups, errors, generated_at: str) -> str:
    def card(item):
        if item["pct"] is None:
            pct_html = '<span class="pct na">数据缺失</span>'
        else:
            up = item["pct"] >= 0
            cls = "up" if up else "down"
            sign = "+" if up else ""
            pct_html = f'<span class="pct {cls}">{sign}{item["pct"]:.2f}%</span>'
        return f'''
        <div class="card">
          <div class="name">{item["name"]}&nbsp;&nbsp;{item["value"]}</div>
          <div class="value">{pct_html}</div>
        </div>'''

    groups_html = ""
    for g in groups:
        cards = "".join(card(i) for i in g["items"])
        groups_html += f'''
      <div class="group" style="background:{g["bg"]}">
        <div class="group-title">{g["title"]}</div>
        <div class="row">{cards}</div>
      </div>'''

    errors_html = ""
    if errors:
        items = "".join(f"<li>{e}</li>" for e in errors)
        errors_html = f'''
      <div class="warning">
        <strong>⚠️ 以下指数抓取失败，请人工核实：</strong>
        <ul>{items}</ul>
      </div>'''

    return f'''<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<title>每日全球股指速览</title>
<style>
  body {{ font-family: "Microsoft YaHei", "PingFang SC", Arial, sans-serif;
         background:#fff; margin:0; padding:24px; color:#333; }}
  h1 {{ font-size:20px; margin-bottom:4px; }}
  .timestamp {{ color:#888; font-size:13px; margin-bottom:20px; }}
  .group {{ border-radius:6px; padding:14px 18px; margin-bottom:16px; }}
  .group-title {{ font-size:13px; color:#555; margin-bottom:8px; font-weight:bold; }}
  .row {{ display:flex; flex-wrap:wrap; gap:12px; }}
  .card {{ flex:1; min-width:160px; text-align:center; padding:8px 4px; }}
  .name {{ font-size:15px; font-weight:bold; color:#222; margin-bottom:6px; }}
  .pct {{ font-size:15px; font-weight:bold; }}
  .pct.up {{ color:#c0392b; }}      /* 红涨 */
  .pct.down {{ color:#2e7d32; }}    /* 绿跌 */
  .pct.na {{ color:#999; font-weight:normal; font-size:13px; }}
  .warning {{ background:#fff3cd; border:1px solid #ffe08a; padding:12px 16px;
              border-radius:6px; font-size:13px; color:#7a5b00; margin-top:20px; }}
  .warning ul {{ margin:6px 0 0 18px; padding:0; }}
  .source-note {{ color:#aaa; font-size:11px; margin-top:24px; }}
</style>
</head>
<body>
  <h1>每日全球主要股指速览</h1>
  <div class="timestamp">数据生成时间（新加坡时间）：{generated_at}</div>
  {groups_html}
  {errors_html}
  <div class="source-note">数据来源：Yahoo Finance（免费公开数据，可能有数分钟延迟，仅供参考，不构成投资建议）</div>
</body>
</html>'''


def main():
    sgt = timezone(timedelta(hours=8))
    now_sgt = datetime.now(sgt).strftime("%Y-%m-%d %H:%M")

    groups, errors = build_report()

    # 写 JSON 快照，便于排查
    with open("indices.json", "w", encoding="utf-8") as f:
        json.dump({"generated_at": now_sgt, "groups": groups, "errors": errors},
                   f, ensure_ascii=False, indent=2)

    html = render_html(groups, errors, now_sgt)
    with open("report.html", "w", encoding="utf-8") as f:
        f.write(html)

    print(f"完成，生成时间 {now_sgt}")
    if errors:
        print("以下指数抓取失败：")
        for e in errors:
            print(" -", e)
        # 抓取失败不视为致命错误（比如节假日休市），但打印出来便于人工核对
    return 0


if __name__ == "__main__":
    sys.exit(main())
