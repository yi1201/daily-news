#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每日新闻收集脚本
收集过去24小时的国际国内重大事件、热门舆情、产业新闻、国内重大政策新闻
"""

import feedparser
import requests
import json
import os
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Optional

# ============ 配置 ============

# RSSHub 镜像列表（按优先级排序）
RSSHUB_MIRRORS = [
    "https://rsshub.rssforever.com",
    "https://rsshub.pseudoyu.com", 
    "https://rsshub.fivecc.xyz",
]

# 新闻源配置
NEWS_SOURCES = {
    "国内要闻": {
        "route": "/news/whxw",
        "description": "新华网综合新闻"
    },
    "财经新闻": {
        "route": "/caixin/latest",
        "description": "财新网财经新闻"
    },
    "科技产业": {
        "route": "/36kr/news/latest",
        "description": "36氪科技创业"
    },
    "深度报道": {
        "route": "/thepaper/featured",
        "description": "澎湃新闻深度报道"
    },
    "国际新闻": {
        "route": "/zaobao/realtime/china",
        "description": "联合早报国际新闻"
    },
    "财经快讯": {
        "route": "/wallstreetcn/news/global",
        "description": "华尔街见闻财经快讯"
    },
    "科技商业": {
        "route": "/huxiu/article",
        "description": "虎嗅科技商业"
    },
}

# 飞书 Webhook（从环境变量读取）
FEISHU_WEBHOOK = os.environ.get("FEISHU_WEBHOOK", "")

# 时间阈值（过去24小时）
TIME_THRESHOLD = timedelta(hours=24)

# ============ 核心函数 ============

def fetch_rss(route: str) -> List[Dict]:
    """
    从 RSSHub 获取 RSS 数据
    尝试多个镜像，返回第一个成功的结果
    """
    for mirror in RSSHUB_MIRRORS:
        try:
            url = f"{mirror}{route}"
            print(f"尝试从 {mirror} 获取 {route}...")
            feed = feedparser.parse(url)
            
            if feed.entries:
                print(f"✅ 成功从 {mirror} 获取 {len(feed.entries)} 条")
                return feed.entries
            else:
                print(f"⚠️ {mirror} 返回空数据")
                
        except Exception as e:
            print(f"❌ {mirror} 失败: {e}")
            continue
    
    print(f"❌ 所有镜像都无法获取 {route}")
    return []


def parse_date(entry) -> Optional[datetime]:
    """解析 RSS 条目的发布时间"""
    try:
        # 尝试不同的日期字段
        if hasattr(entry, 'published_parsed') and entry.published_parsed:
            return datetime(*entry.published_parsed[:6])
        elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
            return datetime(*entry.updated_parsed[:6])
        else:
            return None
    except Exception as e:
        print(f"日期解析失败: {e}")
        return None


def filter_recent_entries(entries: List[Dict]) -> List[Dict]:
    """过滤出过去24小时内的条目"""
    now = datetime.now()
    recent_entries = []
    
    for entry in entries:
        pub_date = parse_date(entry)
        if pub_date:
            # 处理时区问题，假设RSS时间是UTC
            time_diff = now - pub_date
            if time_diff <= TIME_THRESHOLD:
                recent_entries.append(entry)
        else:
            # 无法解析日期，默认保留
            recent_entries.append(entry)
    
    return recent_entries


def format_news_entry(entry, index: int) -> str:
    """格式化单条新闻"""
    title = entry.get('title', '无标题')
    link = entry.get('link', '')
    
    # 尝试获取摘要
    summary = ""
    if hasattr(entry, 'summary'):
        summary = entry.summary[:100] + "..." if len(entry.summary) > 100 else entry.summary
    
    text = f"{index}. {title}"
    if summary:
        text += f"\n   {summary}"
    text += f"\n   🔗 {link}\n"
    
    return text


def format_category_news(category: str, entries: List[Dict], description: str) -> str:
    """格式化某个分类的新闻"""
    if not entries:
        return ""
    
    lines = [
        f"📰 {category}",
        f"   {description}",
        "-" * 40
    ]
    
    for i, entry in enumerate(entries[:5], 1):  # 每个分类最多5条
        lines.append(format_news_entry(entry, i))
    
    return "\n".join(lines)


def send_to_feishu(content: str) -> bool:
    """发送消息到飞书"""
    if not FEISHU_WEBHOOK:
        print("⚠️ 未设置 FEISHU_WEBHOOK 环境变量")
        print("消息内容预览:")
        print(content[:500] + "..." if len(content) > 500 else content)
        return False
    
    today = datetime.now().strftime('%Y年%m月%d日')
    
    payload = {
        "msg_type": "post",
        "content": {
            "post": {
                "zh_cn": {
                    "title": f"📢 早间新闻播报 ({today})",
                    "content": [
                        [{"tag": "text", "text": content}]
                    ]
                }
            }
        }
    }
    
    try:
        response = requests.post(
            FEISHU_WEBHOOK,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get("code") == 0:
                print("✅ 消息发送成功")
                return True
            else:
                print(f"❌ 飞书返回错误: {result}")
                return False
        else:
            print(f"❌ HTTP错误: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ 发送失败: {e}")
        return False


def collect_all_news() -> Dict[str, List[Dict]]:
    """收集所有新闻源的数据"""
    all_news = {}
    
    for category, config in NEWS_SOURCES.items():
        print(f"\n{'='*50}")
        print(f"正在收集: {category}")
        print(f"{'='*50}")
        
        entries = fetch_rss(config["route"])
        
        if entries:
            # 过滤过去24小时的新闻
            recent_entries = filter_recent_entries(entries)
            all_news[category] = recent_entries
            print(f"✅ {category}: 获取 {len(entries)} 条，筛选后 {len(recent_entries)} 条")
        else:
            all_news[category] = []
            print(f"❌ {category}: 获取失败")
    
    return all_news


def format_all_news(all_news: Dict[str, List[Dict]]) -> str:
    """格式化所有新闻为文本"""
    sections = []
    
    for category, config in NEWS_SOURCES.items():
        entries = all_news.get(category, [])
        if entries:
            section = format_category_news(category, entries, config["description"])
            if section:
                sections.append(section)
    
    if not sections:
        return "⚠️ 今天没有获取到新闻，请检查数据源"
    
    # 添加统计信息
    total = sum(len(entries) for entries in all_news.values())
    header = f"📊 共收集 {total} 条新闻\n"
    header += f"⏰ 收集时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
    header += "=" * 40 + "\n\n"
    
    return header + "\n\n".join(sections)


def main():
    """主函数"""
    print("🚀 开始收集每日新闻...")
    print(f"⏰ 当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📊 配置的新闻源: {len(NEWS_SOURCES)} 个")
    print("=" * 60)
    
    # 收集新闻
    all_news = collect_all_news()
    
    # 格式化
    content = format_all_news(all_news)
    
    print("\n" + "=" * 60)
    print("📤 准备发送消息...")
    print("=" * 60)
    
    # 发送到飞书
    success = send_to_feishu(content)
    
    if success:
        print("\n✅ 任务完成")
        return 0
    else:
        print("\n❌ 任务失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
