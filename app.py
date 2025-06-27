# app.py

import yaml
import requests
import streamlit as st
from pathlib import Path
from datetime import date
from concurrent.futures import ThreadPoolExecutor, as_completed
import re

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

if config["auth_token"] and not CONFIG_PATH.exists():
    save_config(config)
    st.sidebar.success("Config created")


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


@st.cache_data(show_spinner=False)
def load_persons():
    """Return mapping of name -> id for known persons."""
    try:
        r = session.get("https://v2api.musicalligator.com/api/persons?name=")
        if r.status_code == 200:
            return {p["name"]: p["id"] for p in r.json().get("data", [])}
    except Exception:
        pass
    return {}

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

config.setdefault("artists", {})
selected_artists = st.sidebar.multiselect(
    "Artists", list(artist_map.keys()),
    default=list(config["artists"].keys()), key="artist_select"
)
config["artists"] = {name: artist_map[name] for name in selected_artists if name in artist_map}

config.setdefault("labels", {})
for name, lid in label_map.items():
    config["labels"].setdefault(name, lid)

# Presets per artist
st.sidebar.markdown("### Presets (per-artist)")
presets_ui = {}
for artist_name in config["artists"]:
    default = config.get("presets", {}).get(artist_name, {})
    exp = st.sidebar.expander(artist_name, expanded=False)
    # Label
    names = list(config["labels"].keys())
    ids   = list(config["labels"].values())
    sel   = default.get("label_id")
    idx   = ids.index(sel) if sel in ids else 0
    p_label = exp.selectbox("Label", names, index=idx, key=f"lbl_{artist_name}")
    # Genre
    p_genre = exp.number_input(
        "Main Genre ID",
        value=default.get("genre_id", 0),
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
    persons = load_persons()
    person_names = list(persons.keys())
    comp_default = [
        next((n for n, pid in persons.items() if pid == cid), str(cid))
        for cid in default.get("composers", [])
    ]
    lyric_default = [
        next((n for n, pid in persons.items() if pid == lid), str(lid))
        for lid in default.get("lyricists", [])
    ]
    comp_sel = exp.multiselect(
        "Composers", person_names, default=comp_default, key=f"comp_{artist_name}"
    )
    lyric_sel = exp.multiselect(
        "Lyricists", person_names, default=lyric_default, key=f"lyric_{artist_name}"
    )
    presets_ui[artist_name] = {
        "label_id":     config["labels"][p_label],
        "genre_id":     p_genre,
        "recording_year": p_year,
        "language_id":  p_lang,
        "composers":    [persons[n] for n in comp_sel if n in persons],
        "lyricists":    [persons[n] for n in lyric_sel if n in persons]
    }
config["presets"] = presets_ui

if st.sidebar.button("Save config", key="save_config"):
    save_config(config)
    st.sidebar.success("Config saved")

max_workers = st.sidebar.number_input(
    "Parallel uploads", min_value=1, max_value=5, value=1, step=1, key="workers"
)

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

found = []
for base, files in groups.items():
    title_part = base.split(" - ",1)[1] if " - " in base else base
    ver = ""
    m = re.search(r"\(([^()]*)\)\s*$", title_part)
    if m:
        ver = m.group(1).strip()
    found.append({
        "Base": base,
        "Artist": base.split(" - ",1)[0] if " - " in base else "",
        "Title": title_part,
        "Version": ver,
        "Cover": "✅" if "cover" in files else "⚠️",
        "Audio": "✅" if "audio" in files else "⚠️"
    })
st.table(found)

track_settings = {}
for base, files in groups.items():
    artist = base.split(" - ",1)[0] if " - " in base else base
    with st.expander(base, expanded=False):
        p_exp = st.checkbox("Explicit", value=False, key=f"ex_{base}")
        p_date = st.date_input("Track Date", value=date.today(), key=f"td_{base}")
    track_settings[base] = {"explicit": p_exp, "track_date": p_date.isoformat()}


def batch_update_tracks(release_id, track_list, sess):
    st.write("→ Updating track metadata…")
    for meta in track_list:
        tid = meta.get("trackId")
        data = {k: v for k, v in meta.items() if k != "trackId"}
        r = sess.put(
            f"https://v2api.musicalligator.com/api/releases/{release_id}/tracks/{tid}",
            json=data
        )
        st.write(f"Track {tid} update: {r.status_code}")
        if r.status_code >= 400:
            st.write(r.text)


def get_label_name(label_id: int) -> str:
    for name, lid in config.get("labels", {}).items():
        if lid == label_id:
            return name
    return ""


def set_release_label(release_id: int, label_id: int, year: int, sess):
    label = get_label_name(label_id)
    data = {
        "labelId": label_id,
        "clineValue": label,
        "plineValue": label,
        "clineYear": str(year),
        "plineYear": str(year),
    }
    st.write("→ Setting label…")
    r = sess.put(
        f"https://v2api.musicalligator.com/api/releases/{release_id}",
        json=data,
    )
    st.write(f"Label update: {r.status_code}")
    if r.status_code >= 400:
        st.write(r.text)

def upload_release(base, files, opts):
    local = requests.Session()
    local.headers.update(session.headers)
    artist, title = (base.split(" - ", 1) + [""])[:2]
    version = ""
    m = re.search(r"\(([^()]*)\)\s*$", title)
    if m:
        version = m.group(1).strip()
        title = title[:m.start()].rstrip()
    if artist not in config["artists"]:
        st.error(f"Нет artist_id для '{artist}'")
        return
    preset = config["presets"][artist]
    main_genre = preset.get("genre_id")
    artist_id = config["artists"][artist]

    # 1) Создать черновик
    st.write(f"→ Creating draft for '{title}'…")
    r1 = local.post(
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
    track_date = opts.get("track_date", date.today().isoformat())
    track_list = []
    meta_release = {
        "title": title,
        "releaseDate": track_date,
        "originalReleaseDate": track_date,
        "status": "DRAFT",
        "client": {"id": artist_id},
        "artists": [{"id": artist_id, "role": "MAIN"}],
        "genre":      {"genreId": main_genre},
        "tracks":     [{"trackId": track0}],
        "countries":  []
    }
    if version:
        meta_release["releaseVersion"] = version
    r2 = local.put(
        f"https://v2api.musicalligator.com/api/releases/{rid}",
        json=meta_release
    )
    st.write(f"Metadata updated: {r2.status_code}")
    if r2.status_code >= 400:
        st.write(r2.text)

    # 2a) Установить лейбл
    label_id = preset.get("label_id")
    if label_id:
        year = date.fromisoformat(track_date).year
        set_release_label(rid, label_id, year, local)


    # 3) Upload cover
    if "cover" in files:
        st.write("→ Uploading cover…")
        r3 = local.post(
            f"https://v2api.musicalligator.com/api/releases/{rid}/cover",
            files={"file": (files["cover"].name, files["cover"], "image/png")}
        )
        st.write(f"Cover upload: {r3.status_code}")
        if r3.status_code >= 400:
            st.write(r3.text)

    # 4) Upload audio на правильный endpoint
    if "audio" in files:
        st.write("→ Uploading audio…")
        fa = files["audio"]
        r4 = local.post(
            f"https://v2api.musicalligator.com/api/releases/{rid}/tracks/{track0}/upload",
            files={"file": (fa.name, fa, "audio/wav")}
        )
        st.write(f"Audio upload: {r4.status_code}")
        if r4.status_code not in (200, 201):
            st.error("Audio upload failed")
            st.write(r4.text)
            return

        # 5) Обновить метаданные трека
        if not preset.get("composers") or not preset.get("lyricists"):
            st.warning(f"Отсутствуют composers/lyricists для {artist}")
        st.write("→ Preparing track metadata…")
        persons = [
            {"id": c, "role": "MUSIC_AUTHOR"} for c in preset["composers"]
        ] + [
            {"id": l, "role": "LYRICS_AUTHOR"} for l in preset["lyricists"]
        ]
        track_meta = {
            "trackId": track0,
            "artist":   artist_id,
            "artists":  [{"id": artist_id, "role": "MAIN"}],
            "title":    title,
            "trackVersion": version if version else None,
            "genre":    {"genreId": main_genre},
            "recordingYear":  preset["recording_year"],
            "language":       preset["language_id"],
            "composers":      preset["composers"],
            "lyricists":      preset["lyricists"],
            "persons":        persons,
            "adult":          opts.get("explicit", False),
            "trackDate":      opts.get("track_date")
        }
        if track_meta["trackVersion"] is None:
            del track_meta["trackVersion"]

        track_list.append(track_meta)

    if track_list:
        batch_update_tracks(rid, track_list, local)

    st.success(f"Release {rid} done!")
    st.markdown(f"[Открыть релиз](https://app.musicalligator.ru/releases/{rid})")

if st.button("Run upload", key="upload_button"):
    total = len(groups)
    progress = st.progress(0.0)
    done = 0
    futures = []
    with ThreadPoolExecutor(max_workers=max_workers) as exe:
        for base, files in groups.items():
            opts = track_settings.get(base, {})
            futures.append(exe.submit(upload_release, base, files, opts))
        for _ in as_completed(futures):
            done += 1
            progress.progress(done / total)
    st.balloons()
