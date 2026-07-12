#!/usr/bin/env python3
"""
MCP (Model Context Protocol) Server for ziyuanzhan
资源站监测 MCP 服务器 - 为 AI 工具提供资源站数据查询能力
"""
import asyncio
import json
import os
from datetime import datetime
from typing import Any
from mcp.server.fastmcp import FastMCP

# 初始化 MCP 服务器
mcp = FastMCP("ziyuanzhan-monitor", description="ziyuanzu.com 资源站监测服务")

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
DOCS_DIR = os.path.join(os.path.dirname(__file__), "docs")

def load_latest_data() -> dict:
    """加载最新的监测数据"""
    latest_file = os.path.join(DATA_DIR, "latest.json")
    if os.path.exists(latest_file):
        with open(latest_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"resources": [], "timestamp": None, "stats": {}}

@mcp.tool()
def get_all_resources() -> str:
    """
    获取所有监测的资源站列表及其状态信息
    
    返回：所有资源站的详细信息，包括名称、链接、状态、响应时间等
    """
    data = load_latest_data()
    resources = data.get("resources", [])
    timestamp = data.get("timestamp", "未知")
    
    result = f"📊 资源站监测数据 (更新时间: {timestamp})\n\n"
    result += f"共监测 {len(resources)} 个资源站\n\n"
    
    for idx, r in enumerate(resources, 1):
        health = r.get("health", {})
        status = "✅ 在线" if health.get("is_alive") else "❌ 离线"
        resp_time = health.get("response_time_ms", "-")
        status_code = health.get("status_code", "-")
        
        result += f"{idx}. {r.get('name', '未知')}\n"
        result += f"   链接: {r.get('link', '-')}\n"
        result += f"   状态: {status}\n"
        result += f"   HTTP状态码: {status_code}\n"
        result += f"   响应时间: {resp_time}ms\n"
        result += f"   可用率: {r.get('uptime', '-')}\n"
        result += f"   资源量: {r.get('resource_count', '-')}\n"
        result += "\n"
    
    return result

@mcp.tool()
def get_online_resources() -> str:
    """
    获取当前所有在线的资源站列表
    
    返回：仅包含在线（可访问）的资源站信息
    """
    data = load_latest_data()
    resources = data.get("resources", [])
    
    online = [r for r in resources if r.get("health", {}).get("is_alive", False)]
    
    result = f"✅ 在线资源站 ({len(online)} 个):\n\n"
    
    for idx, r in enumerate(online, 1):
        health = r.get("health", {})
        result += f"{idx}. {r.get('name', '未知')}\n"
        result += f"   🔗 {r.get('link', '-')}\n"
        result += f"   ⏱️ {health.get('response_time_ms', '-')}ms\n"
        result += "\n"
    
    return result

@mcp.tool()
def get_offline_resources() -> str:
    """
    获取当前所有离线的资源站列表
    
    返回：仅包含离线（不可访问）的资源站信息及错误原因
    """
    data = load_latest_data()
    resources = data.get("resources", [])
    
    offline = [r for r in resources if not r.get("health", {}).get("is_alive", False)]
    
    result = f"❌ 离线资源站 ({len(offline)} 个):\n\n"
    
    for idx, r in enumerate(offline, 1):
        health = r.get("health", {})
        error = health.get("error", "未知错误")
        result += f"{idx}. {r.get('name', '未知')}\n"
        result += f"   🔗 {r.get('link', '-')}\n"
        result += f"   原因: {error}\n"
        result += "\n"
    
    return result

@mcp.tool()
def get_statistics() -> str:
    """
    获取资源站监测统计信息
    
    返回：总体统计数据，包括在线率、响应时间分布等
    """
    data = load_latest_data()
    resources = data.get("resources", [])
    timestamp = data.get("timestamp", "未知")
    
    total = len(resources)
    online = sum(1 for r in resources if r.get("health", {}).get("is_alive", False))
    offline = total - online
    rate = (online / total * 100) if total > 0 else 0
    
    # 计算响应时间统计
    resp_times = []
    for r in resources:
        rt = r.get("health", {}).get("response_time_ms")
        if rt and isinstance(rt, (int, float)):
            resp_times.append(rt)
    
    avg_rt = sum(resp_times) / len(resp_times) if resp_times else 0
    max_rt = max(resp_times) if resp_times else 0
    min_rt = min(resp_times) if resp_times else 0
    
    result = f"📈 资源站监测统计\n"
    result += f"{'='*40}\n"
    result += f"更新时间: {timestamp}\n\n"
    result += f"总计资源站: {total} 个\n"
    result += f"✅ 在线: {online} 个\n"
    result += f"❌ 离线: {offline} 个\n"
    result += f"📊 在线率: {rate:.1f}%\n\n"
    result += f"⏱️ 响应时间统计:\n"
    result += f"   平均: {avg_rt:.1f}ms\n"
    result += f"   最快: {min_rt:.1f}ms\n"
    result += f"   最慢: {max_rt:.1f}ms\n"
    
    return result

@mcp.tool()
def search_resource(keyword: str) -> str:
    """
    根据关键词搜索资源站
    
    参数:
        keyword: 搜索关键词（资源站名称或描述）
    
    返回：匹配的资源站信息
    """
    data = load_latest_data()
    resources = data.get("resources", [])
    
    keyword_lower = keyword.lower()
    matches = []
    
    for r in resources:
        name = r.get("name", "").lower()
        desc = r.get("description", "").lower()
        if keyword_lower in name or keyword_lower in desc:
            matches.append(r)
    
    if not matches:
        return f"🔍 未找到包含 '{keyword}' 的资源站"
    
    result = f"🔍 搜索 '{keyword}' 结果 ({len(matches)} 个):\n\n"
    
    for idx, r in enumerate(matches, 1):
        health = r.get("health", {})
        status = "✅" if health.get("is_alive") else "❌"
        result += f"{idx}. {status} {r.get('name', '未知')}\n"
        result += f"   🔗 {r.get('link', '-')}\n"
        result += f"   📝 {r.get('description', '-')[:50]}...\n"
        result += "\n"
    
    return result

@mcp.tool()
def get_fastest_resources(limit: int = 5) -> str:
    """
    获取响应速度最快的资源站
    
    参数:
        limit: 返回数量，默认5个
    
    返回：按响应时间排序的最快资源站列表
    """
    data = load_latest_data()
    resources = data.get("resources", [])
    
    # 筛选有响应时间数据且在线的站点
    valid = []
    for r in resources:
        health = r.get("health", {})
        rt = health.get("response_time_ms")
        if health.get("is_alive") and rt and isinstance(rt, (int, float)):
            valid.append((r, rt))
    
    # 按响应时间排序
    valid.sort(key=lambda x: x[1])
    fastest = valid[:limit]
    
    result = f"⚡ 响应最快的资源站 (Top {len(fastest)}):\n\n"
    
    for idx, (r, rt) in enumerate(fastest, 1):
        result += f"{idx}. {r.get('name', '未知')}\n"
        result += f"   🔗 {r.get('link', '-')}\n"
        result += f"   ⏱️ {rt}ms\n"
        result += "\n"
    
    return result

@mcp.resource("data://latest")
def get_latest_data_resource() -> str:
    """
    MCP 资源：最新监测数据 JSON
    """
    data = load_latest_data()
    return json.dumps(data, ensure_ascii=False, indent=2)

@mcp.resource("stats://summary")
def get_stats_resource() -> str:
    """
    MCP 资源：统计摘要
    """
    data = load_latest_data()
    resources = data.get("resources", [])
    
    total = len(resources)
    online = sum(1 for r in resources if r.get("health", {}).get("is_alive", False))
    
    stats = {
        "timestamp": data.get("timestamp"),
        "total": total,
        "online": online,
        "offline": total - online,
        "online_rate": round(online / total * 100, 1) if total > 0 else 0,
        "source": data.get("source")
    }
    
    return json.dumps(stats, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    print("🚀 启动 ziyuanzhan MCP 服务器")
    print("=" * 50)
    print("可用工具:")
    print("  - get_all_resources: 获取所有资源站")
    print("  - get_online_resources: 获取在线资源站")
    print("  - get_offline_resources: 获取离线资源站")
    print("  - get_statistics: 获取统计信息")
    print("  - search_resource: 搜索资源站")
    print("  - get_fastest_resources: 获取最快资源站")
    print("=" * 50)
    mcp.run()
