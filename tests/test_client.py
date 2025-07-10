from __future__ import annotations

from src.musicalligator_client import DEFAULT_HEADERS, MusicAlligatorClient


def test_session_headers() -> None:
    client = MusicAlligatorClient("token")
    for k, v in DEFAULT_HEADERS.items():
        assert client.session.headers.get(k) == v
    assert client.session.headers.get("Authorization") == "token"


def test_url_helper() -> None:
    client = MusicAlligatorClient("token")
    assert client._url("/path") == "https://v2api.musicalligator.com/api/path"
    assert client._url("http://example.com") == "http://example.com"
