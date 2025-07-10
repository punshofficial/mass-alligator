from __future__ import annotations

from typing import Any

import requests  # type: ignore
import streamlit as st

BASE_URL = "https://v2api.musicalligator.com/api"
DEFAULT_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "X-LANG": "RU",
    "X-Requested-With": "XMLHttpRequest",
    "Origin": "https://app.musicalligator.ru",
    "Referer": "https://app.musicalligator.ru/",
}


class MusicAlligatorClient:
    """Simple wrapper for MusicAlligator API."""

    def __init__(self, token: str, base_url: str = BASE_URL) -> None:
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({"Authorization": token, **DEFAULT_HEADERS})

    def _url(self, path: str) -> str:
        return (
            path if path.startswith("http") else f"{self.base_url}/{path.lstrip('/')}"
        )

    def get(self, path: str, **kwargs: Any) -> requests.Response:
        try:
            return self.session.get(self._url(path), **kwargs)
        except Exception as exc:  # noqa: BLE001
            st.toast(f"Ошибка запроса GET {path}: {exc}")
            raise

    def post(self, path: str, **kwargs: Any) -> requests.Response:
        try:
            return self.session.post(self._url(path), **kwargs)
        except Exception as exc:  # noqa: BLE001
            st.toast(f"Ошибка запроса POST {path}: {exc}")
            raise

    def put(self, path: str, **kwargs: Any) -> requests.Response:
        try:
            return self.session.put(self._url(path), **kwargs)
        except Exception as exc:  # noqa: BLE001
            st.toast(f"Ошибка запроса PUT {path}: {exc}")
            raise

    def clone_session(self) -> requests.Session:
        """Return a new session with copied headers."""
        sess = requests.Session()
        sess.headers.update(self.session.headers)
        return sess
