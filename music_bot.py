#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Музыкальный бот-парсер для Telegram каналов (@leaksffm и источников с #новинки).
- Парсит свежие треки из публичных превью Telegram.
- Различает RU и EN исполнителей.
- Автоматически находит и прикрепляет стильную музыкальную обложку.
- Формирует описания с дерзким сленгом и хэштегами.
"""
import os
import sys
import csv
import json
import random
import time
import requests
from bs4 import BeautifulSoup
from pathlib import Path
from datetime import datetime, timezone

BASE = Path(__file__).resolve().parent
STATE_DIR = BASE / "state"
STATE_CSV = STATE_DIR / "music_state.csv"

SOURCES = ["leaksffm", "novinki_muzyk", "newtracks", "leakspremiere"]

RU_SLANG_INTROS = [
    "🔥 Главный бэнгер этой недели:",
    "⚡ Этот трек разнесет все чарты:",
    "🖤 Новый звук, который ты ждал:",
    "💎 Чистый кач и мощный вайб:",
    "🌪️ Трек, от которого мурашки:"
]

EN_SLANG_INTROS = [
    "🔥 Pure fire on repeat:",
    "⚡ Absolute chart-breaker:",
    "🖤 The vibe is unmatched:",
    "💎 Fresh drop you need right now:",
    "🌪️ Heavy rotation material:"
]

RU_HASHTAGS = ["новинки", "музыка", "трек", "премьера", "хит", "звук", "рэп", "поп", "чарт", "кач", "вайб"]
EN_HASHTAGS = ["newmusic", "track", "premiere", "hit", "vibes", "audio", "rap", "pop", "chart", "fire", "fresh"]

def log(msg: str):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)

def load_state():
    uploaded = set()
    if STATE_CSV.exists():
        with open(STATE_CSV, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                uploaded.add(r["post_id"])
    return uploaded

def save_state(post_id: str):
    STATE_DIR.mkdir(exist_ok=True)
    file_exists = STATE_CSV.exists()
    with open(STATE_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["post_id", "upload_date"])
        if not file_exists:
            writer.writeheader()
        writer.writerow({"post_id": post_id, "upload_date": datetime.now(timezone.utc).isoformat()})

def is_russian(text: str) -> bool:
    return any('а' <= c <= 'я' or 'А' <= c <= 'Я' for c in text)

def fetch_tracks_from_telegram(channel: str):
    url = f"https://t.me/s/{channel}"
    tracks = []
    try:
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        if resp.status_code != 200:
            return []
        soup = BeautifulSoup(resp.text, 'html.parser')
        messages = soup.find_all('div', class_='tgme_widget_message')
        for msg in messages:
            post_id = msg.get('data-post', '')
            text_el = msg.find('div', class_='tgme_widget_message_text')
            text = text_el.get_text(separator=" ").strip() if text_el else ""
            if text:
                tracks.append({"post_id": post_id or text[:30], "text": text})
    except Exception as e:
        log(f"Ошибка парсинга {channel}: {e}")
    return tracks

def get_random_music_cover():
    client_id = os.environ.get("UNSPLASH_ACCESS_KEY", "DEMO_KEY")
    url = "https://api.unsplash.com/photos/random"
    queries = ["music album cover aesthetic vinyl cyberpunk dark", "concert DJ festival neon music vibe", "artist studio microphone moody portrait"]
    params = {"query": random.choice(queries), "client_id": client_id}
    try:
        resp = requests.get(url, params=params, timeout=10)
        if resp.status_code == 200:
            return resp.json()["urls"]["regular"]
    except Exception:
        pass
    return "https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?q=80&w=1200&fm=jpg"

def send_telegram_photo(bot_token: str, channel_id: str, photo_url: str, caption: str):
    url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
    data = {"chat_id": channel_id, "photo": photo_url, "caption": caption, "parse_mode": "HTML"}
    return requests.post(url, data=data, timeout=30).json()

def main():
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    channel_id = os.environ.get("TELEGRAM_CHANNEL_ID", "")
    if not (bot_token and channel_id):
        sys.exit("Ошибка: не заданы секреты.")

    uploaded = load_state()
    all_tracks = []
    for s in SOURCES:
        all_tracks.extend(fetch_tracks_from_telegram(s))

    if not all_tracks:
        log("Треки не найдены.")
        return

    random.shuffle(all_tracks)
    published = 0
    for t in all_tracks:
        if published >= 3:
            break
        post_id = t["post_id"]
        if post_id in uploaded:
            continue

        raw_text = t["text"]
        clean_text = raw_text[:300] + "..." if len(raw_text) > 300 else raw_text
        is_ru = is_russian(clean_text)

        intro = random.choice(RU_SLANG_INTROS if is_ru else EN_SLANG_INTROS)
        tags = random.sample(RU_HASHTAGS if is_ru else EN_HASHTAGS, 5)
        tags_str = " ".join([f"#{tag}" for tag in tags])
        cover = get_random_music_cover()

        caption = f"{intro}\n\n<b>{clean_text}</b>\n\n🎧 Слушай на повторе!\n\n{tags_str}"
        res = send_telegram_photo(bot_token, channel_id, cover, caption)
        if res.get("ok"):
            save_state(post_id)
            published += 1
            time.sleep(3)

if __name__ == "__main__":
    main()
