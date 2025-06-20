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
        "default": {
            "label_id": 0,
            "genre_id": 0,
            "platform_ids": []
        },
        "artists": {},
        "labels": {},
        "presets": {}
    }

def save_config(cfg):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.safe_dump(cfg, f)

config = load_config()

# —————————————
# Sidebar: config UI
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
    "Default Label ID",
    value=defaults.get("label_id", 0),
    step=1,
    key="default_label"
)
genre_id = st.sidebar.number_input(
    "Default Genre ID",
    value=defaults.get("genre_id", 0),
    step=1,
    key="default_genre"
)
def_platforms = st.sidebar.text_input(
    "Default Platform IDs (comma-separated)",
    ",".join(str(x) for x in defaults.get("platform_ids", [])),
    key="default_platforms"
)
config["default"] = {
    "label_id": label_id,
    "genre_id": genre_id,
    "platform_ids": [int(x) for x in def_platforms.split(",") if x.strip().isdigit()]
}

# Prepare API session
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
    art_resp = session.get("https://v2api.musicalligator.com/api/artists?name=")
    artist_map = {a["name"]: a["id"] for a in art_resp.json().get("data", [])}
except:
    artist_map = {}
try:
    lbl_resp = session.get(
        "https://v2api.musicalligator.com/api/labels?_status=READY&level=REGULAR&skip=0&limit=100"
    )
    lbl_data = lbl_resp.json().get("data", {}).get("data", [])
    label_map = {l["name"]: l["id"] for l in lbl_data}
except:
    label_map = {}

# Sidebar: Artist mappings
st.sidebar.markdown("### Artist mappings")
config.setdefault("artists", {})
for name, aid in artist_map.items():
    config["artists"].setdefault(name, aid)
artists_raw = st.sidebar.text_area(
    "Artists (Name:id per line)",
    value="\n".join(f"{n}:{i}" for n, i in config["artists"].items()),
    height=120,
    key="artists_text"
)
new_artists = {}
for line in artists_raw.splitlines():
    if ":" in line:
        n, v = line.split(":", 1)
        if v.strip().isdigit():
            new_artists[n.strip()] = int(v.strip())
config["artists"] = new_artists

# Sidebar: Label mappings
st.sidebar.markdown("### Label mappings")
config.setdefault("labels", {})
for name, lid in label_map.items():
    config["labels"].setdefault(name, lid)
labels_raw = st.sidebar.text_area(
    "Labels (Name:id per line)",
    value="\n".join(f"{n}:{i}" for n, i in config["labels"].items()),
    height=120,
    key="labels_text"
)
new_labels = {}
for line in labels_raw.splitlines():
    if ":" in line:
        n, v = line.split(":", 1)
        if v.strip().isdigit():
            new_labels[n.strip()] = int(v.strip())
config["labels"] = new_labels

# Sidebar: Presets per artist
st.sidebar.markdown("### Presets (per-artist)")
presets_ui = {}
for artist_name in config["artists"]:
    default = config.get("presets", {}).get(artist_name, {})
    exp = st.sidebar.expander(artist_name, expanded=False)
    label_names = list(config["labels"].keys())
    label_ids = list(config["labels"].values())
    sel_label = default.get("label_id", label_id)
    default_idx = label_ids.index(sel_label) if sel_label in label_ids else 0
    p_label = exp.selectbox("Label", label_names, index=default_idx, key=f"preset_lbl_{artist_name}")
    p_genre = exp.number_input("Genre ID", value=default.get("genre_id", genre_id), step=1, key=f"preset_genre_{artist_name}")
    p_year  = exp.number_input("Recording Year", value=default.get("recording_year", date.today().year), step=1, key=f"preset_year_{artist_name}")
    p_lang  = exp.number_input("Language ID", value=default.get("language_id", 7), step=1, key=f"preset_lang_{artist_name}")
    comps   = exp.text_input("Composer IDs", value=",".join(str(x) for x in default.get("composers", [])), key=f"preset_comps_{artist_name}")
    lyrics  = exp.text_input("Lyricist IDs", value=",".join(str(x) for x in default.get("lyricists", [])), key=f"preset_lyrics_{artist_name}")

    presets_ui[artist_name] = {
        "label_id": config["labels"][p_label],
        "genre_id": p_genre,
        "recording_year": p_year,
        "language_id": p_lang,
        "composers": [int(x) for x in comps.split(",") if x.strip().isdigit()],
        "lyricists": [int(x) for x in lyrics.split(",") if x.strip().isdigit()]
    }
config["presets"] = presets_ui

# Save config
if st.sidebar.button("Save config", key="save_config"):
    save_config(config)
    st.sidebar.success("config.yaml saved")

# —————————————
# Main UI
# —————————————
st.title("Batch Upload Releases")
st.markdown("Перетащите файлы PNG и WAV или выберите папки:")

covers = st.file_uploader("Обложки (PNG)", type=["png"], accept_multiple_files=True)
wavs   = st.file_uploader("Аудио (WAV)", type=["wav"], accept_multiple_files=True)

groups = {}
for f in covers:
    groups.setdefault(Path(f.name).stem, {})["cover"] = f
for f in wavs:
    groups.setdefault(Path(f.name).stem, {})["audio"] = f

st.write("Найдено релизов:")
st.table([
    {
        "Base": base,
        "Artist": base.split(" - ", 1)[0] if " - " in base else "",
        "Title":  base.split(" - ", 1)[1] if " - " in base else base,
        "Cover":  "✅" if "cover" in files else "⚠️",
        "Audio":  "✅" if "audio" in files else "⚠️"
    }
    for base, files in groups.items()
])

st.header("Параметры")
release_date = st.date_input("Release Date", date.today())
orig_date    = st.date_input("Original Release Date", date.today())

def upload_release(base, files):
    artist_name, title = (base.split(" - ", 1) + [None])[:2]
    if artist_name not in config["artists"]:
        st.error(f"Artist '{artist_name}' not in config")
        return

    preset = config["presets"].get(artist_name, {})
    artist_id = config["artists"][artist_name]

    # 1. Create draft
    st.write(f"→ Creating draft for '{base}'…")
    r1 = session.post(
        "https://v2api.musicalligator.com/api/releases/create",
        json={"releaseType": "SINGLE"}
    )
    if r1.status_code != 201:
        st.error(f"Create error: {r1.status_code} {r1.text}")
        return
    rid = r1.json()["data"]["release"]["releaseId"]
    st.write(f"Draft {rid} created")

    # 2. Update metadata (with artist) 
    track0 = r1.json()["data"]["release"]["tracks"][0]["trackId"]
    meta = {
        "title": title,
        "releaseDate": release_date.isoformat(),
        "originalReleaseDate": orig_date.isoformat(),
        "clineYear": str(release_date.year),
        "clineValue": artist_name,
        "plineYear": str(release_date.year),
        "plineValue": artist_name,
        "status": "DRAFT",
        "client": {"id": artist_id},
        "artists": [{"id": artist_id, "role": "MAIN"}],
        "labelId": preset.get("label_id", config["default"]["label_id"]),
        "genres": [{"genreId": preset.get("genre_id", config["default"]["genre_id"])}],
        "tracks": [{"trackId": track0}],
        "streamingPlatforms": config["default"]["platform_ids"],
        "countries": []
    }
    r2 = session.put(f"https://v2api.musicalligator.com/api/releases/{rid}", json=meta)
    st.write(f"Metadata updated: {r2.status_code}")

    # 3. Upload cover
    if "cover" in files:
        st.write("→ Uploading cover…")
        fc = files["cover"]
        r3 = session.post(
            f"https://v2api.musicalligator.com/api/releases/{rid}/cover",
            files={"file": (fc.name, fc, "image/png")}
        )
        st.write(f"Cover upload: {r3.status_code}")

    # 4. Upload audio to correct endpoint :contentReference[oaicite:0]{index=0}
    if "audio" in files:
        st.write("→ Uploading audio…")
        fa = files["audio"]
        r4 = session.post(
            f"https://v2api.musicalligator.com/api/releases/{rid}/tracks/{track0}/upload",
            files={"file": (fa.name, fa, "audio/wav")}
        )
        st.write(f"Audio upload: {r4.status_code}")
        if r4.status_code == 200:
            tid = r4.json()["data"]["track"]["trackId"]
            # 5. Update track metadata
            tm = {
                "recordingYear": preset.get("recording_year", release_date.year),
                "language":     preset.get("language_id", 7),
                "composers":    preset.get("composers", []),
                "lyricists":    preset.get("lyricists", [])
            }
            r5 = session.put(f"https://v2api.musicalligator.com/api/tracks/{tid}", json=tm)
            st.write(f"Track metadata updated: {r5.status_code}")

    # 6. Set platforms
    st.write("→ Setting platforms…")
    r6 = session.put(
        f"https://v2api.musicalligator.com/api/releases/{rid}/platforms",
        json={"platformIds": config["default"]["platform_ids"]}
    )
    st.write(f"Platforms set: {r6.status_code}")

    st.success(f"Release {rid} done!")

if st.button("Запустить загрузку", key="upload_button"):
    for base, files in groups.items():
        upload_release(base, files)
    st.balloons()
