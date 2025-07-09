from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
import requests  # type: ignore
import streamlit as st
import yaml  # type: ignore

CONFIG_PATH = Path("config.yaml")

# Release statuses supported by the API
STATUS_OPTIONS = [
    "DRAFT",
    "MODERATE",
    "WAITING",
    "RELEASED",
    "EDIT",
    "ERROR",
]


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


def fetch_releases(
    artist_id: int, status: str, session: requests.Session
) -> List[Dict[str, Any]]:
    """Return releases for the artist with the given status."""

    payload = {
        "status": status,
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
            all_releases = r.json().get("data", {}).get("data", [])
            return [
                d
                for d in all_releases
                if any(a.get("id") == artist_id for a in d.get("artists", []))
            ]
        st.toast(f"Ошибка загрузки: {r.status_code}")
    except Exception as exc:  # noqa: BLE001
        st.toast(f"Ошибка запроса: {exc}")
    return []


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


def load_release_list() -> None:
    artist_id = artists[st.session_state.sel_artist]
    status = st.session_state.sel_status
    st.session_state.release_list = fetch_releases(artist_id, status, session)
    st.session_state.stats = {
        s: len(fetch_releases(artist_id, s, session))
        for s in ["DRAFT", "MODERATE", "WAITING"]
    }


st.selectbox(
    "Артист",
    list(artists.keys()),
    key="sel_artist",
    on_change=load_release_list,
)
st.selectbox(
    "Статус",
    STATUS_OPTIONS,
    key="sel_status",
    on_change=load_release_list,
)

if "release_list" not in st.session_state:
    st.session_state.sel_artist = list(artists.keys())[0]
    st.session_state.sel_status = STATUS_OPTIONS[0]
    load_release_list()

if st.session_state.get("stats"):
    col1, col2, col3 = st.columns(3)
    col1.metric("Черновиков", st.session_state.stats.get("DRAFT", 0))
    col2.metric("На модерации", st.session_state.stats.get("MODERATE", 0))
    col3.metric("Ожидают", st.session_state.stats.get("WAITING", 0))

if st.session_state.release_list:
    id_to_name = {v: k for k, v in artists.items()}
    rows = []
    for d in st.session_state.release_list:
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
        load_release_list()
else:
    st.info("Нет релизов")
