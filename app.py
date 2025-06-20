# app.py

import yaml
import requests
import streamlit as st
from pathlib import Path
from datetime import date

# —————————————
# Config load & save
# —————————————
CONFIG_PATH = Path("config.yaml")

def load_config():
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {
        "auth_token": "",
        "default": {"label_id": 0, "genre_id": 0, "platform_ids": []},
        "artists": {},
        "labels": {},
        "presets": {}
    }

def save_config(cfg):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.safe_dump(cfg, f)

config = load_config()

# —————————————
# Sidebar: Config UI
# —————————————
st.sidebar.title("Настройки")

config["auth_token"] = st.sidebar.text_input(
    "Token",
    config.get("auth_token", ""),
    type="password",
    key="token_input"
).strip()

st.sidebar.markdown("### Default settings")
defaults = config.get("default", {})
label_id = st.sidebar.number_input(
    "Default Label ID", defaults.get("label_id", 0), step=1, key="default_label"
)
genre_id = st.sidebar.number_input(
    "Default Genre ID", defaults.get("genre_id", 0), step=1, key="default_genre"
)
platforms_raw = st.sidebar.text_input(
    "Default Platform IDs (comma)",
    ",".join(str(x) for x in defaults.get("platform_ids", [])),
    key="default_platforms"
)
platform_ids = [int(x) for x in platforms_raw.split(",") if x.strip().isdigit()]
config["default"] = {"label_id": label_id, "genre_id": genre_id, "platform_ids": platform_ids}

# Prepare HTTP session
session = requests.Session()
session.headers.update({
    "Authorization": config["auth_token"],
    "Accept": "application/json, text/plain, */*",
    "X-LANG": "RU",
    "X-Requested-With": "XMLHttpRequest",
    "Origin": "https://app.musicalligator.ru",
    "Referer": "https://app.musicalligator.ru/"
})

# Fetch artists & labels
try:
    art = session.get("https://v2api.musicalligator.com/api/artists?name=").json().get("data", [])
    artist_map = {a["name"]: a["id"] for a in art}
except:
    artist_map = {}
try:
    lbl = session.get(
        "https://v2api.musicalligator.com/api/labels?_status=READY&level=REGULAR&skip=0&limit=100"
    ).json().get("data", {}).get("data", [])
    label_map = {l["name"]: l["id"] for l in lbl}
except:
    label_map = {}

# Artist mappings
st.sidebar.markdown("### Artist mappings")
config.setdefault("artists", {})
for n, i in artist_map.items():
    config["artists"].setdefault(n, i)
artists_raw = st.sidebar.text_area(
    "Artists (Name:id per line)",
    "\n".join(f"{n}:{i}" for n, i in config["artists"].items()),
    height=120, key="artists_text"
)
new_artists = {}
for line in artists_raw.splitlines():
    if ":" in line:
        n, v = line.split(":", 1)
        if v.strip().isdigit():
            new_artists[n.strip()] = int(v.strip())
config["artists"] = new_artists

# Label mappings
st.sidebar.markdown("### Label mappings")
config.setdefault("labels", {})
for n, i in label_map.items():
    config["labels"].setdefault(n, i)
labels_raw = st.sidebar.text_area(
    "Labels (Name:id per line)",
    "\n".join(f"{n}:{i}" for n, i in config["labels"].items()),
    height=120, key="labels_text"
)
new_labels = {}
for line in labels_raw.splitlines():
    if ":" in line:
        n, v = line.split(":", 1)
        if v.strip().isdigit():
            new_labels[n.strip()] = int(v.strip())
config["labels"] = new_labels

# Presets per artist
st.sidebar.markdown("### Presets (per-artist)")
presets_ui = {}
for artist_name in config["artists"]:
    default = config.get("presets", {}).get(artist_name, {})
    exp = st.sidebar.expander(artist_name, expanded=False)
    # Label
    names = list(config["labels"].keys())
    ids   = list(config["labels"].values())
    sel   = default.get("label_id", label_id)
    idx   = ids.index(sel) if sel in ids else 0
    p_label = exp.selectbox("Label", names, index=idx, key=f"lbl_{artist_name}")
    # Genre
    p_genre = exp.number_input(
        "Main Genre ID",
        value=default.get("genre_id", genre_id),
        step=1,
        key=f"genre_{artist_name}"
    )
    # Track defaults
    p_year = exp.number_input(
        "Recording Year",
        value=default.get("recording_year", date.today().year),
        step=1, key=f"year_{artist_name}"
    )
    p_lang = exp.number_input(
        "Language ID",
        value=default.get("language_id", 7),
        step=1, key=f"lang_{artist_name}"
    )
    comps  = exp.text_input(
        "Composer IDs (comma)", ",".join(str(x) for x in default.get("composers", [])),
        key=f"comp_{artist_name}"
    )
    lyrics = exp.text_input(
        "Lyricist IDs (comma)", ",".join(str(x) for x in default.get("lyricists", [])),
        key=f"lyric_{artist_name}"
    )
    presets_ui[artist_name] = {
        "label_id":     config["labels"][p_label],
        "genre_id":     p_genre,
        "recording_year": p_year,
        "language_id":  p_lang,
        "composers":    [int(x) for x in comps.split(",") if x.strip().isdigit()],
        "lyricists":    [int(x) for x in lyrics.split(",") if x.strip().isdigit()]
    }
config["presets"] = presets_ui

if st.sidebar.button("Save config", key="save_config"):
    save_config(config)
    st.sidebar.success("Config saved")

# —————————————
# Main UI
# —————————————
st.title("Batch Upload Releases")
st.markdown("Drag & drop your PNG (cover) and WAV (audio) files:")

covers = st.file_uploader("Covers (PNG)", type=["png"], accept_multiple_files=True)
wavs   = st.file_uploader("Audio (WAV)", type=["wav"], accept_multiple_files=True)

# Group files by base name
groups = {}
for f in covers:
    groups.setdefault(Path(f.name).stem, {})["cover"] = f
for f in wavs:
    groups.setdefault(Path(f.name).stem, {})["audio"] = f

st.write("Found releases:")
st.table([
    {
        "Base": base,
        "Artist": base.split(" - ",1)[0] if " - " in base else "",
        "Title":  base.split(" - ",1)[1] if " - " in base else base,
        "Cover":  "✅" if "cover" in files else "⚠️",
        "Audio":  "✅" if "audio" in files else "⚠️"
    }
    for base, files in groups.items()
])

st.header("Parameters")
release_date = st.date_input("Release Date", date.today())
orig_date    = st.date_input("Original Release Date", date.today())

def upload_release(base, files):
    artist, title = (base.split(" - ", 1) + [""])[:2]
    if artist not in config["artists"]:
        st.error(f"Нет artist_id для '{artist}'")
        return
    preset = config["presets"][artist]
    artist_id = config["artists"][artist]

    # 1) Создать черновик
    st.write(f"→ Creating draft for '{title}'…")
    r1 = session.post(
        "https://v2api.musicalligator.com/api/releases/create",
        json={"releaseType":"SINGLE"}
    )
    if r1.status_code != 201:
        st.error(f"Create failed: {r1.status_code} {r1.text}")
        return
    rid = r1.json()["data"]["release"]["releaseId"]
    st.write(f"Draft {rid} created")

    # 2) Обновить базовые метаданные релиза
    track0 = r1.json()["data"]["release"]["tracks"][0]["trackId"]
    meta_release = {
        "title": title,
        "releaseDate": release_date.isoformat(),
        "originalReleaseDate": orig_date.isoformat(),
        "status": "DRAFT",
        "client": {"id": artist_id},
        "artists": [{"id": artist_id, "role": "MAIN"}],
        "labelId":    preset["label_id"],
        "genres":     [{"genreId": preset["genre_id"]}],
        "tracks":     [{"trackId": track0}],
        "countries":  [],
        "platformIds": config["default"].get("platform_ids", [])
    }
    r2 = session.put(f"https://v2api.musicalligator.com/api/releases/{rid}", json=meta_release)
    st.write(f"Metadata updated: {r2.status_code}")

    if config["default"].get("platform_ids"):
        r_platforms = session.put(
            f"https://v2api.musicalligator.com/api/releases/{rid}/platforms",
            json=config["default"]["platform_ids"]
        )
        st.write(f"Platforms set: {r_platforms.status_code}")

    # 3) Upload cover
    if "cover" in files:
        st.write("→ Uploading cover…")
        r3 = session.post(
            f"https://v2api.musicalligator.com/api/releases/{rid}/cover",
            files={"file": (files["cover"].name, files["cover"], "image/png")}
        )
        st.write(f"Cover upload: {r3.status_code}")

    # 4) Upload audio на правильный endpoint
    if "audio" in files:
        st.write("→ Uploading audio…")
        fa = files["audio"]
        r4 = session.post(
            f"https://v2api.musicalligator.com/api/releases/{rid}/tracks/{track0}/upload",
            files={"file": (fa.name, fa, "audio/wav")}
        )
        st.write(f"Audio upload: {r4.status_code}")
        if r4.status_code not in (200, 201):
            st.error("Audio upload failed")
            return

        # 5) Обновить метаданные трека
        st.write("→ Updating track metadata…")
        track_meta = {
            "genres":         [preset["genre_id"]],
            "recordingYear":  preset["recording_year"],
            "language":       preset["language_id"],
            "composers":      preset["composers"],
            "lyricists":      preset["lyricists"]
        }
        r5 = session.put(
            f"https://v2api.musicalligator.com/api/tracks/{track0}",
            json=track_meta
        )
        st.write(f"Track metadata updated: {r5.status_code}")

    st.success(f"Release {rid} done!")
    st.markdown(f"[Открыть релиз](https://app.musicalligator.ru/releases/{rid})")

if st.button("Run upload", key="upload_button"):
    for base, files in groups.items():
        upload_release(base, files)
    st.balloons()
