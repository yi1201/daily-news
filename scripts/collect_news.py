#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每日新闻收集脚本
"""

import feedparser
import requests
import os
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Optional

# RSSHub 镜像列表
RSSHUB_MIRRORS = [
    "https://rsshub.rssforever.com",
    "https://rsshub.pseudoyu.com", 
    "https://rsshub.fivecc.xyz",
]

# 新闻源配置
NEWS_SOURCES = {
    "国内重大政策": {
        "route": "/gov/zhengce/zhengceku",
        "description": "中国政府网政策文件"
    },
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
    "极客公园": {
        "route": "/geekpark",
        "description": "极客公园科技"
    },
    "第一财经": {
        "route": "/yicai",
        "description": "第一财经财经"
    },
    "微博热搜": {
        "route": "/weibo/search/hot",
        "description": "微博热搜榜"
    },
}

FEISHU_WEBHOOK = os.environ.get("FEISHU_WEBHOOK", "")
TIME_THRESHOLD = timedelta(hours=24)

def fetch_rss(route: str) -> List[Dict]:
"""从 RSSHub 获取 RSS 数据"""
for mirror in RSSHUB_MIRRORS:
try:
url = f"{mirror}{route}"
print(f"尝试从 {mirror} 获取 {route}...")
feed = feedparser.parse(url)
if feed.entries:
print(f"✅ 成功从 {mirror} 获取 {len(feed.entries)} 条")
return feed.entries
except Exception as e:
print(f"❌ {mirror} 失败: {e}")
continue
return []

def parse_date(entry) -> Optional[datetime]:
"""解析 RSS 条目的发布时间"""
try:
if hasattr(entry, 'published_parsed') and entry.published_parsed:
return datetime(*entry.published_parsed[:6])
elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
return datetime(*entry.updated_parsed[:6])
except:
pass
return None

def filter_recent_entries(entries: List[Dict]) -> List[Dict]:
"""过滤出过去24小时内的条目"""
now = datetime.now()
recent = []
for entry in entries:
pub_date = parse_date(entry)
if pub_date and (now - pub_date) <= TIME_THRESHOLD:
recent.append(entry)
elif not pub_date:
recent.append(entry)
return recent

def format_news_entry(entry, index: int) -> str:
"""格式化单条新闻"""
title = entry.get('title', '无标题')
link = entry.get('link', '')
return f"{index}. {title}\n 🔗 {link}\n"

def format_category_news(category: str, entries: List[Dict]) -> str:
"""格式化某个分类的新闻"""
if not entries:
return ""
lines = [f"📰 {category}", "-" * 30]
for i, entry in enumerate(entries[:5], 1):
lines.append(format_news_entry(entry, i))
return "\n".join(lines)

def send_to_feishu(content: str) -> bool:
"""发送消息到飞书"""
if not FEISHU_WEBHOOK:
print("⚠️ 未设置 FEISHU_WEBHOOK")
return False

today = datetime.now().strftime('%Y年%m月%d日')
payload = {
"msg_type": "post",
"content": {
"post": {
"zh_cn": {
"title": f"📢 早间新闻播报 ({today})",
"content": [[{"tag": "text", "text": content}]]
}
}
}
}

try:
response = requests.post(FEISHU_WEBHOOK, json=payload, timeout=30)
return response.status_code == 200 and response.json().get("code") == 0
except Exception as e:
print(f"❌ 发送失败: {e}")
return False

def main():
print("🚀 开始收集每日新闻...")
all_news = {}

for category, config in NEWS_SOURCES.items():
print(f"\n收集: {category}")
entries = fetch_rss(config["route"])
if entries:
all_news[category] = filter_recent_entries(entries)
print(f"✅ {category}: {len(all_news[category])} 条")

sections = []
for category in NEWS_SOURCES.keys():
entries = all_news.get(category, [])
if entries:
section = format_category_news(category, entries)
if section:
sections.append(section)

if not sections:
print("⚠️ 没有获取到新闻")
return 1

total = sum(len(all_news.get(c, [])) for c in NEWS_SOURCES.keys())
header = f"📊 共收集 {total} 条新闻\n{'=' * 40}\n\n"
content = header + "\n\n".join(sections)

print("\n📤 发送消息...")
if send_to_feishu(content):
print("✅ 发送成功")
return 0
else:
print("❌ 发送失败")
return 1

if __name__ == "__main__":
sys.exit(main())
