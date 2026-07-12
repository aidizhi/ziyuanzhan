#!/usr/bin/env python3
"""
ziyuanzu.com 资源站监测脚本
功能：
1. 抓取 ziyuanzu.com 首页资源站数据
2. 检测各资源站可用性（HTTP 状态码 + 响应时间）
3. 生成静态 HTML 页面
4. 保存 JSON 数据供历史对比
"""
import json
import os
import re
import time
from datetime import datetime
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.ziyuanzu.com"
TIMEOUT = 15

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Referer": "https://www.google.com/",
}

def fetch_page(url: str) -> str:
    """获取页面 HTML 内容"""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        print(f"[ERROR] Failed to fetch {url}: {e}")
        return ""

def parse_resources(html: str) -> list[dict]:
    """解析首页资源站列表"""
    soup = BeautifulSoup(html, "lxml")
    resources = []

    # 查找资源站卡片
    cards = soup.find_all("div", class_=re.compile(r"resource-card|source-card|card"))
    if not cards:
        # 备选：查找包含资源站信息的 div
        cards = soup.find_all("div", class_=lambda x: x and "resource" in x.lower())

    for card in cards:
        try:
            # 提取名称
            name_tag = card.find(["h3", "h4", "h5", "a"], class_=re.compile(r"title|name"))
            if not name_tag:
                name_tag = card.find("a")
            name = name_tag.get_text(strip=True) if name_tag else "未知"

            # 提取链接
            link = ""
            if name_tag and name_tag.has_attr("href"):
                link = urljoin(BASE_URL, name_tag["href"])

            # 提取描述
            desc_tag = card.find("p", class_=re.compile(r"desc|description"))
            if not desc_tag:
                desc_tag = card.find("p")
            description = desc_tag.get_text(strip=True) if desc_tag else ""

            # 提取状态
            status_tag = card.find("span", class_=re.compile(r"status|state"))
            status = status_tag.get_text(strip=True) if status_tag else "未知"

            # 提取可用率
            uptime_match = re.search(r"(\d+(?:\.\d+)?)%", description)
            uptime = uptime_match.group(1) + "%" if uptime_match else "-"

            # 提取资源量
            resource_match = re.search(r"(\d+(?:\.\d+)?)\s*万", description)
            resource_count = resource_match.group(0) if resource_match else "-"

            resources.append({
                "name": name,
                "link": link,
                "description": description,
                "status": status,
                "uptime": uptime,
                "resource_count": resource_count,
            })
        except Exception as e:
            print(f"[WARN] Parse card failed: {e}")
            continue

    return resources

def check_site_health(url: str) -> dict:
    """检测单个资源站的健康状态"""
    result = {
        "url": url,
        "status_code": None,
        "response_time_ms": None,
        "is_alive": False,
        "error": None,
    }
    try:
        start = time.time()
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True)
        elapsed = (time.time() - start) * 1000
        result["status_code"] = resp.status_code
        result["response_time_ms"] = round(elapsed, 2)
        result["is_alive"] = resp.status_code < 400
    except requests.exceptions.Timeout:
        result["error"] = "Timeout"
    except requests.exceptions.ConnectionError:
        result["error"] = "Connection Error"
    except Exception as e:
        result["error"] = str(e)
    return result

def generate_html(data: dict, output_path: str):
    """生成静态 HTML 页面"""
    now = data["timestamp"]
    resources = data["resources"]
    stats = data["stats"]

    total = len(resources)
    alive = sum(1 for r in resources if r.get("health", {}).get("is_alive", False))
    dead = total - alive

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>资源组监测 - ziyuanzu.com 资源站实时监控</title>
<meta name="description" content="ziyuanzu.com 资源站实时监测面板，共监测{total}个资源站，在线{alive}个，离线{dead}个。更新时间：{now}">
<meta name="keywords" content="资源组, ziyuanzu, 影视资源站, 采集站监测, 资源站监控, 播放源检测">
<style>
  :root {{
    --bg: #0f172a;
    --surface: #1e293b;
    --surface2: #334155;
    --ink: #f1f5f9;
    --muted: #94a3b8;
    --accent: #38bdf8;
    --accent2: #818cf8;
    --success: #4ade80;
    --danger: #f87171;
    --warning: #fbbf24;
  }}
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Noto Sans SC", sans-serif;
    background: var(--bg);
    color: var(--ink);
    line-height: 1.6;
    min-height: 100vh;
  }}
  .container {{ max-width: 1200px; margin: 0 auto; padding: 2rem 1rem; }}
  header {{
    text-align: center;
    padding: 2rem 1rem;
    border-bottom: 1px solid var(--surface2);
    margin-bottom: 2rem;
  }}
  header h1 {{ font-size: 2rem; font-weight: 800; color: var(--accent); margin-bottom: 0.5rem; }}
  header .subtitle {{ color: var(--muted); font-size: 1rem; }}
  header .update-time {{ color: var(--muted); font-size: 0.85rem; margin-top: 0.5rem; }}
  .stats-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 1rem;
    margin-bottom: 2rem;
  }}
  .stat-card {{
    background: var(--surface);
    border-radius: 12px;
    padding: 1.5rem;
    text-align: center;
    border: 1px solid var(--surface2);
    transition: transform 0.2s;
  }}
  .stat-card:hover {{ transform: translateY(-4px); }}
  .stat-card .number {{ font-size: 2rem; font-weight: 800; }}
  .stat-card .label {{ color: var(--muted); font-size: 0.85rem; margin-top: 0.25rem; }}
  .stat-card.total .number {{ color: var(--accent); }}
  .stat-card.online .number {{ color: var(--success); }}
  .stat-card.offline .number {{ color: var(--danger); }}
  .stat-card.rate .number {{ color: var(--warning); }}
  .section-title {{
    font-size: 1.3rem;
    font-weight: 700;
    margin: 2rem 0 1rem;
    padding-bottom: 0.5rem;
    border-bottom: 2px solid var(--accent);
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }}
  .resource-table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 0.9rem;
    background: var(--surface);
    border-radius: 12px;
    overflow: hidden;
  }}
  .resource-table thead {{ background: var(--surface2); }}
  .resource-table th, .resource-table td {{ padding: 0.85rem 1rem; text-align: left; }}
  .resource-table th {{ font-weight: 600; color: var(--muted); font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.05em; }}
  .resource-table tbody tr {{ border-bottom: 1px solid var(--surface2); transition: background 0.15s; }}
  .resource-table tbody tr:hover {{ background: rgba(56,189,248,0.05); }}
  .resource-table tbody tr:last-child {{ border-bottom: none; }}
  .badge {{
    display: inline-block;
    padding: 0.2rem 0.6rem;
    border-radius: 4px;
    font-size: 0.75rem;
    font-weight: 600;
  }}
  .badge-online {{ background: rgba(74,222,128,0.15); color: var(--success); }}
  .badge-offline {{ background: rgba(248,113,113,0.15); color: var(--danger); }}
  .badge-unknown {{ background: rgba(251,191,36,0.15); color: var(--warning); }}
  .resource-name {{ font-weight: 600; color: var(--accent); text-decoration: none; }}
  .resource-name:hover {{ text-decoration: underline; }}
  .resource-desc {{ color: var(--muted); font-size: 0.8rem; }}
  .response-fast {{ color: var(--success); }}
  .response-slow {{ color: var(--warning); }}
  .response-timeout {{ color: var(--danger); }}
  .footer {{
    text-align: center;
    padding: 2rem;
    color: var(--muted);
    font-size: 0.85rem;
    border-top: 1px solid var(--surface2);
    margin-top: 3rem;
  }}
  .footer a {{ color: var(--accent); text-decoration: none; }}
  @media (max-width: 768px) {{
    .resource-table {{ font-size: 0.8rem; }}
    .resource-table th, .resource-table td {{ padding: 0.6rem 0.5rem; }}
    .resource-desc {{ display: none; }}
    header h1 {{ font-size: 1.5rem; }}
  }}
</style>
</head>
<body>
<div class="container">
<header>
  <h1>资源组监测</h1>
  <p class="subtitle">ziyuanzu.com 资源站实时监控面板</p>
  <p class="update-time">更新时间：{now}</p>
</header>
<div class="stats-grid">
  <div class="stat-card total">
    <div class="number">{total}</div>
    <div class="label">监测资源站</div>
  </div>
  <div class="stat-card online">
    <div class="number">{alive}</div>
    <div class="label">在线站点</div>
  </div>
  <div class="stat-card offline">
    <div class="number">{dead}</div>
    <div class="label">离线站点</div>
  </div>
  <div class="stat-card rate">
    <div class="number">{round(alive/total*100,1) if total else 0}%</div>
    <div class="label">在线率</div>
  </div>
</div>
<h2 class="section-title">资源站状态列表</h2>
<table class="resource-table">
  <thead>
    <tr>
      <th>#</th>
      <th>资源站名称</th>
      <th>描述</th>
      <th>状态</th>
      <th>HTTP状态</th>
      <th>响应时间</th>
      <th>可用率</th>
    </tr>
  </thead>
  <tbody>
"""

    for idx, r in enumerate(resources, 1):
        health = r.get("health", {})
        is_alive = health.get("is_alive", False)
        status_code = health.get("status_code", "-")
        resp_time = health.get("response_time_ms")
        error = health.get("error")

        if is_alive:
            badge = '<span class="badge badge-online">在线</span>'
            resp_class = "response-fast" if resp_time and resp_time < 1000 else "response-slow"
            resp_text = f'{resp_time}ms' if resp_time else '-'
        elif error:
            badge = '<span class="badge badge-offline">离线</span>'
            resp_class = "response-timeout"
            resp_text = error
        else:
            badge = '<span class="badge badge-unknown">未知</span>'
            resp_class = "response-timeout"
            resp_text = '-'

        html += f"""
    <tr>
      <td>{idx}</td>
      <td><a class="resource-name" href="{r.get('link', '#')}" target="_blank" rel="noopener">{r.get('name', '未知')}</a></td>
      <td class="resource-desc">{r.get('description', '')}</td>
      <td>{badge}</td>
      <td>{status_code}</td>
      <td class="{resp_class}">{resp_text}</td>
      <td>{r.get('uptime', '-')}</td>
    </tr>
"""

    html += f"""
  </tbody>
</table>
<div class="footer">
  <p>数据来源：<a href="https://www.ziyuanzu.com/" target="_blank" rel="noopener">ziyuanzu.com</a> | 监测脚本自动运行</p>
  <p style="margin-top:0.5rem;">本项目为第三方监测工具，与 ziyuanzu.com 官方无关</p>
</div>
</div>
</body>
</html>
"""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[INFO] HTML generated: {output_path}")

def save_json(data: dict, output_path: str):
    """保存 JSON 数据"""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"[INFO] JSON saved: {output_path}")

def main():
    print("=" * 50)
    print("ziyuanzu.com 资源站监测脚本")
    print("=" * 50)

    # 1. 抓取首页
    print("\n[1/4] 抓取首页数据...")
    html = fetch_page(BASE_URL)
    if not html:
        print("[ERROR] 首页抓取失败，退出")
        return

    # 2. 解析资源站列表
    print("[2/4] 解析资源站列表...")
    resources = parse_resources(html)
    print(f"[INFO] 解析到 {len(resources)} 个资源站")

    # 3. 检测每个资源站的健康状态
    print("[3/4] 检测资源站健康状态...")
    for i, r in enumerate(resources):
        link = r.get("link", "")
        if link:
            print(f"  [{i+1}/{len(resources)}] 检测: {r.get('name', '未知')} ... ", end="", flush=True)
            health = check_site_health(link)
            r["health"] = health
            status = "在线" if health["is_alive"] else "离线"
            print(f"{status} ({health.get('status_code') or health.get('error')})")
        else:
            r["health"] = {"is_alive": False, "error": "No URL"}

    # 4. 生成数据
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    data = {
        "timestamp": timestamp,
        "source": BASE_URL,
        "resources": resources,
        "stats": {
            "total": len(resources),
            "alive": sum(1 for r in resources if r.get("health", {}).get("is_alive", False)),
        },
    }

    # 5. 保存文件
    print("\n[4/4] 生成输出文件...")
    generate_html(data, "docs/index.html")
    save_json(data, f"data/monitor_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    save_json(data, "data/latest.json")

    print("\n" + "=" * 50)
    print("监测完成！")
    print(f"- HTML 页面: docs/index.html")
    print(f"- JSON 数据: data/latest.json")
    print("=" * 50)

if __name__ == "__main__":
    main()
