from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
import requests  # type: ignore
import streamlit as st
import yaml  # type: ignore

CONFIG_PATH = Path("config.yaml")


def load_config() -> Dict[str, Any]:
    if CONFIG_PATH.exists():
        with CONFIG_PATH.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


def build_session(token: str) -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "Authorization": token,
            "Accept": "application/json, text/plain, */*",
            "X-LANG": "RU",
            "X-Requested-With": "XMLHttpRequest",
            "Origin": "https://app.musicalligator.ru",
            "Referer": "https://app.musicalligator.ru/",
        }
    )
    return session


def fetch_drafts(artist_id: int, session: requests.Session) -> List[Dict[str, Any]]:
    """Return list of draft releases for the artist."""

    payload = {
        "status": "DRAFT",
        "search": "",
        "startDate": None,
        "endDate": None,
        "limit": 50,
        "skip": 0,
        "_changes": True,
        "clientId": artist_id,
    }

    try:
        r = session.post(
            "https://v2api.musicalligator.com/api/releases",
            json=payload,
        )
        if r.status_code in (200, 201):
            all_drafts = r.json().get("data", {}).get("data", [])
            return [
                d
                for d in all_drafts
                if any(a.get("id") == artist_id for a in d.get("artists", []))
            ]
        st.toast(f"Ошибка загрузки: {r.status_code}")
    except Exception as exc:  # noqa: BLE001
        st.toast(f"Ошибка запроса: {exc}")
    return []


def moderate_release(release_id: int, session: requests.Session) -> bool:
    try:
        r = session.put(
            f"https://v2api.musicalligator.com/api/releases/{release_id}/status/moderate"
        )
        return r.status_code == 200
    except Exception as exc:  # noqa: BLE001
        st.toast(f"Ошибка модерации {release_id}: {exc}")
        return False


config = load_config()

st.set_page_config(page_title="Модерация релизов", layout="wide")
st.title("📤 Массовая отправка на модерацию")

if not config.get("auth_token"):
    st.error("Отсутствует токен в config.yaml")
    st.stop()

artists: Dict[str, int] = config.get("artists", {})
if not artists:
    st.error("В config.yaml нет артистов")
    st.stop()

session = build_session(config["auth_token"])

artist_name = st.selectbox("Артист", list(artists.keys()))

if "drafts" not in st.session_state:
    st.session_state.drafts = []  # type: ignore[attr-defined]

if st.button("Обновить список"):
    st.session_state.drafts = fetch_drafts(artists[artist_name], session)

if st.session_state.drafts:
    id_to_name = {v: k for k, v in artists.items()}
    rows = []
    for d in st.session_state.drafts:
        ids = [a.get("id") for a in d.get("artists", [])]
        names = [id_to_name.get(i, str(i)) for i in ids]
        date = d.get("releaseDate", "")
        if isinstance(date, str) and "T" in date:
            date = date.split("T")[0]
        rows.append(
            {
                "ID": d.get("releaseId"),
                "Название": d.get("title", ""),
                "Версия": d.get("releaseVersion", ""),
                "Артист": ", ".join(names),
                "Дата релиза": date,
                "select": False,
            }
        )
    edited = st.data_editor(
        pd.DataFrame(rows),
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        column_config={"select": st.column_config.CheckboxColumn("Отправить")},
        key="release_table",
    )
    selected_ids = edited[edited["select"]]["ID"].tolist()
    if st.button("Отправить выбранные") and selected_ids:
        for rid in selected_ids:
            if moderate_release(int(rid), session):
                st.toast(f"Релиз {rid} отправлен")
            else:
                st.toast(f"Ошибка при отправке {rid}")
else:
    st.info("Нет загруженных черновиков")
