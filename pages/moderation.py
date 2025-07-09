from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
import requests  # type: ignore
import streamlit as st
import yaml  # type: ignore

CONFIG_PATH = Path("config.yaml")

# Release statuses supported by the API
# Statuses available for filtering
STATUS_OPTIONS = [
    "DRAFT",
    "MODERATE",
    "WAITING",
    "PROCESSED",
    "RELEASED",
    "EDIT",
    "ERROR",
    "REMOVED",
]

# Some API endpoints use alternative names
STATUS_QUERY_MAP: Dict[str, str] = {"PROCESSED": "UPLOADED"}

# Labels for Russian UI
STATUS_LABELS: Dict[str, str] = {
    "DRAFT": "Черновиков",
    "MODERATE": "На модерации",
    "WAITING": "Ожидают отгрузки",
    "PROCESSED": "Отгружен",
    "RELEASED": "Выпущено",
    "EDIT": "Редактируются",
    "ERROR": "Ошибки",
    "REMOVED": "Удалены",
}


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
    limit = 50
    skip = 0
    query_status = STATUS_QUERY_MAP.get(status, status)
    payload = {
        "status": query_status,
        "search": "",
        "startDate": None,
        "endDate": None,
        "limit": limit,
        "skip": skip,
        "_changes": True,
        "artistId": artist_id,
    }

    releases: List[Dict[str, Any]] = []
    try:
        while True:
            r = session.post(
                "https://v2api.musicalligator.com/api/releases",
                json=payload,
            )
            if r.status_code not in (200, 201):
                st.toast(f"Ошибка загрузки: {r.status_code}")
                return releases
            data = r.json().get("data", {}).get("data", [])
            releases.extend(data)
            if len(data) < limit:
                break
            skip += limit
            payload["skip"] = skip
    except Exception as exc:  # noqa: BLE001
        st.toast(f"Ошибка запроса: {exc}")
    return releases


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
        s: (
            len(st.session_state.release_list)
            if s == status
            else len(fetch_releases(artist_id, s, session))
        )
        for s in STATUS_OPTIONS
    }


if "sel_artist" not in st.session_state:
    st.session_state.sel_artist = list(artists.keys())[0]
if "sel_status" not in st.session_state:
    st.session_state.sel_status = STATUS_OPTIONS[0]
if "release_list" not in st.session_state:
    load_release_list()

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

if st.session_state.get("stats"):
    cols = st.columns(len(STATUS_OPTIONS))
    for col, st_key in zip(cols, STATUS_OPTIONS):
        col.metric(
            STATUS_LABELS.get(st_key, st_key), st.session_state.stats.get(st_key, 0)
        )

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
