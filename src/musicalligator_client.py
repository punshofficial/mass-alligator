from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
import streamlit as st

BASE_URL = "https://v2api.musicalligator.com/api"


class MusicAlligatorClient:
    """Simplified client for MusicAlligator API."""

    def __init__(self, auth_token: str) -> None:
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": auth_token,
                "Accept": "application/json, text/plain, */*",
                "X-LANG": "RU",
                "X-Requested-With": "XMLHttpRequest",
                "Origin": "https://app.musicalligator.ru",
                "Referer": "https://app.musicalligator.ru/",
            }
        )

    def _request(
        self, method: str, endpoint: str, **kwargs: Any
    ) -> Optional[requests.Response]:
        url = f"{BASE_URL}{endpoint}"
        try:
            resp = self.session.request(method, url, **kwargs)
            resp.raise_for_status()
            return resp
        except requests.RequestException as exc:
            st.toast(f"Ошибка запроса {endpoint}: {exc}")
            return None

    # Cached lookups
    @st.cache_data(
        show_spinner=False,
        hash_funcs={requests.Session: id, Path: str, "MusicAlligatorClient": id},
    )
    def get_artists(self) -> Dict[str, int]:
        resp = self._request("GET", "/artists", params={"name": ""})
        if resp is None:
            return {}
        data = resp.json().get("data", [])
        return {item["name"]: item["id"] for item in data}

    @st.cache_data(
        show_spinner=False,
        hash_funcs={requests.Session: id, Path: str, "MusicAlligatorClient": id},
    )
    def get_labels(self) -> Dict[str, int]:
        params = {"_status": "READY", "level": "REGULAR", "skip": 0, "limit": 100}
        resp = self._request("GET", "/labels", params=params)
        if resp is None:
            return {}
        data = resp.json().get("data", {}).get("data", [])
        return {item["name"]: item["id"] for item in data}

    @st.cache_data(
        show_spinner=False,
        hash_funcs={requests.Session: id, Path: str, "MusicAlligatorClient": id},
    )
    def list_releases(self, **params: Any) -> List[Dict[str, Any]]:
        resp = self._request("GET", "/releases", params=params)
        if resp is None:
            return []
        return resp.json().get("data", [])

    @st.cache_data(
        show_spinner=False,
        hash_funcs={requests.Session: id, Path: str, "MusicAlligatorClient": id},
    )
    def get_persons(self) -> Dict[str, int]:
        resp = self._request("GET", "/persons", params={"name": ""})
        if resp is None:
            return {}
        data = resp.json().get("data", [])
        return {item["name"]: item["id"] for item in data}

    def create_release(self) -> Optional[Dict[str, Any]]:
        resp = self._request("POST", "/releases/create", json={"releaseType": "SINGLE"})
        if resp is None:
            return None
        return resp.json().get("data", {}).get("release")

    def update_release(self, release_id: int, data: Dict[str, Any]) -> bool:
        resp = self._request("PUT", f"/releases/{release_id}", json=data)
        return resp is not None

    def upload_cover(self, release_id: int, file) -> bool:
        files = {"file": (file.name, file, "image/png")}
        resp = self._request("POST", f"/releases/{release_id}/cover", files=files)
        return resp is not None

    def upload_audio(self, release_id: int, track_id: int, file) -> bool:
        files = {"file": (file.name, file, "audio/wav")}
        resp = self._request(
            "POST",
            f"/releases/{release_id}/tracks/{track_id}/upload",
            files=files,
        )
        return resp is not None

    def update_track(
        self, release_id: int, track_id: int, data: Dict[str, Any]
    ) -> bool:
        resp = self._request(
            "PUT",
            f"/releases/{release_id}/tracks/{track_id}",
            json=data,
        )
        return resp is not None

    def set_platforms(self, release_id: int, platforms: List[int]) -> bool:
        resp = self._request(
            "PUT",
            f"/releases/{release_id}",
            json={"streamingPlatforms": platforms},
        )
        return resp is not None

    def get_statistics(self, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        resp = self._request("POST", "/statistics", json=payload)
        if resp is None:
            return []
        return resp.json().get("data", [])
