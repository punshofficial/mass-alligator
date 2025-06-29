from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
import streamlit as st
import yaml  # type: ignore

from src.musicalligator_client import MusicAlligatorClient

CONFIG_PATH = Path("config.yaml")


def load_config() -> Dict[str, Any]:
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


config = load_config()
client = MusicAlligatorClient(config.get("auth_token", ""))

st.title("Релизы и статистика")

artist_ids = list(config.get("artists", {}).values())
all_releases: List[Dict[str, Any]] = []
my_releases: List[Dict[str, Any]] = []

with st.spinner("Загружаем список релизов..."):
    all_releases = client.list_releases()
    if artist_ids:
        my_releases = client.list_releases(artists=artist_ids)

st.metric("Всего релизов", len(all_releases))
if artist_ids:
    st.metric("Релизов выбранных артистов", len(my_releases))
else:
    st.warning("Выберите артистов на главной странице")

mode = st.radio(
    "Показывать",
    ["Только выбранных артистов", "Все релизы"],
    index=0 if artist_ids else 1,
    horizontal=True,
)

releases = my_releases if mode == "Только выбранных артистов" else all_releases

if not releases:
    st.info("Нет релизов для отображения")
    st.stop()

artist_map = {v: k for k, v in client.get_artists().items()}

rows: List[Dict[str, Any]] = []
with st.spinner("Загружаем детали релизов..."):
    for r in releases:
        rid = r.get("releaseId")
        if rid is None:
            continue
        info = client.get_release(int(rid))
        if not info:
            continue
        artists = ", ".join(
            artist_map.get(a.get("id"), str(a.get("id")))
            for a in info.get("artists", [])
        )
        title = info.get("title", "")
        ver = info.get("releaseVersion")
        if ver:
            title = f"{title} ({ver})"
        rows.append(
            {
                "title": title,
                "artists": artists,
                "releaseDate": info.get("releaseDate"),
                "label": info.get("label"),
                "ean": info.get("ean") or info.get("ownEan"),
                "status": info.get("status"),
                "link": f"https://app.musicalligator.ru/releases/{r.get('releaseId')}",
                "releaseId": r.get("releaseId"),
            }
        )

df = pd.DataFrame(rows)

st.dataframe(df[["title", "artists", "releaseDate", "label", "ean", "status", "link"]])

if st.button("Показать статистику"):
    payload = {
        "aggs": [{"field": "id_m_list_streaming_platform"}, {"field": "dt_listen"}],
        "filters": [],
        "dates": [],
        "releaseIds": [d["releaseId"] for d in rows],
        "artistIds": artist_ids,
    }
    with st.spinner("Запрос статистики..."):
        stats = client.get_statistics(payload)
    df_stats = pd.DataFrame(stats)
    if not df_stats.empty:
        df_stats["dt_listen"] = pd.to_datetime(df_stats["dt_listen"])
        chart = df_stats.pivot(
            index="dt_listen",
            columns="id_m_list_streaming_platform",
            values="count",
        )
        st.line_chart(chart)
