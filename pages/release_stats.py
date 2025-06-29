from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st
import yaml

from src.musicalligator_client import MusicAlligatorClient

CONFIG_PATH = Path("config.yaml")


def load_config() -> dict:
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


config = load_config()
client = MusicAlligatorClient(config.get("auth_token", ""))

st.title("Релизы и статистика")

artist_ids = list(config.get("artists", {}).values())
if not artist_ids:
    st.warning("Выберите артистов на главной странице")
else:
    with st.spinner("Загружаем релизы..."):
        releases = client.list_releases(artists=artist_ids)

    data = [
        {
            "title": r.get("title"),
            "releaseDate": r.get("releaseDate"),
            "status": r.get("status"),
            "label": r.get("label"),
            "link": f"https://app.musicalligator.ru/releases/{r.get('releaseId')}",
            "releaseId": r.get("releaseId"),
        }
        for r in releases
    ]

    st.metric("Всего релизов", len(data))
    st.dataframe(
        pd.DataFrame(data)[["title", "releaseDate", "status", "label", "link"]]
    )

    if st.button("Показать статистику"):
        payload = {
            "aggs": [
                {"field": "id_m_list_streaming_platform"},
                {"field": "dt_listen"},
            ],
            "filters": [],
            "dates": [],
            "releaseIds": [d["releaseId"] for d in data],
            "artistIds": artist_ids,
        }
        with st.spinner("Запрос статистики..."):
            stats = client.get_statistics(payload)
        df = pd.DataFrame(stats)
        if not df.empty:
            df["dt_listen"] = pd.to_datetime(df["dt_listen"])
            chart = df.pivot(
                index="dt_listen",
                columns="id_m_list_streaming_platform",
                values="count",
            )
            st.line_chart(chart)
