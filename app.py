# app.py

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path

import streamlit as st
import yaml
from streamlit.runtime.uploaded_file_manager import UploadedFile

from src.musicalligator_client import MusicAlligatorClient

try:
    from streamlit.runtime.scriptrunner import add_script_run_ctx
except Exception:  # streamlit<1.25
    add_script_run_ctx = None
import re
import threading

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
        "presets": {},
        "streaming_platforms": [195, 196, 197],
    }


def save_config(cfg):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.safe_dump(cfg, f)


config = load_config()


# Helper to attach Streamlit context to worker threads
def run_with_ctx(fn, *args, **kwargs):
    if add_script_run_ctx:
        add_script_run_ctx(threading.current_thread())
    return fn(*args, **kwargs)


# —————————————
# Sidebar: Config UI
# —————————————
st.sidebar.title("Настройки")

config["auth_token"] = st.sidebar.text_input(
    "Токен", config.get("auth_token", ""), type="password", key="token_input"
).strip()

if config["auth_token"] and not CONFIG_PATH.exists():
    save_config(config)
    st.sidebar.success("Конфигурация создана")


# Prepare HTTP client
client = MusicAlligatorClient(config["auth_token"])
session = client.session


@st.cache_data(show_spinner=False)
def load_persons():
    """Return mapping of name -> id for known persons."""
    try:
        r = client.get("/persons?name=")
        if r.status_code == 200:
            return {p["name"]: p["id"] for p in r.json().get("data", [])}
    except Exception:
        pass
    return {}


# Fetch artists & labels
try:
    art = client.get("/artists?name=").json().get("data", [])
    artist_map = {a["name"]: a["id"] for a in art}
except:
    artist_map = {}
try:
    lbl = (
        client.get("/labels?_status=READY&level=REGULAR&skip=0&limit=100")
        .json()
        .get("data", {})
        .get("data", [])
    )
    label_map = {l["name"]: l["id"] for l in lbl}
except:
    label_map = {}

config.setdefault("artists", {})
selected_artists = st.sidebar.multiselect(
    "Артисты",
    list(artist_map.keys()),
    default=list(config["artists"].keys()),
    key="artist_select",
)
config["artists"] = {
    name: artist_map[name] for name in selected_artists if name in artist_map
}

config.setdefault("labels", {})
for name, lid in label_map.items():
    config["labels"].setdefault(name, lid)

config.setdefault("streaming_platforms", [195, 196, 197])
platforms_text = st.sidebar.text_input(
    "Площадки (через запятую)",
    ",".join(str(p) for p in config.get("streaming_platforms", [])),
    key="platforms_input",
)
try:
    config["streaming_platforms"] = [
        int(x) for x in platforms_text.split(",") if x.strip()
    ]
except ValueError:
    st.sidebar.error("Некорректные ID площадок")

# Presets per artist
st.sidebar.markdown("### Пресеты (для артиста)")
presets_ui = {}
for artist_name in config["artists"]:
    default = config.get("presets", {}).get(artist_name, {})
    exp = st.sidebar.expander(artist_name, expanded=False)
    # Label
    names = list(config["labels"].keys())
    ids = list(config["labels"].values())
    sel = default.get("label_id")
    idx = ids.index(sel) if sel in ids else 0
    p_label = exp.selectbox("Лейбл", names, index=idx, key=f"lbl_{artist_name}")
    # Genre
    p_genre = exp.number_input(
        "ID основного жанра",
        value=default.get("genre_id", 0),
        step=1,
        key=f"genre_{artist_name}",
    )
    # Track defaults
    p_year = exp.number_input(
        "Год записи",
        value=default.get("recording_year", date.today().year),
        step=1,
        key=f"year_{artist_name}",
    )
    p_lang = exp.number_input(
        "ID языка",
        value=default.get("language_id", 7),
        step=1,
        key=f"lang_{artist_name}",
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
        "Композиторы", person_names, default=comp_default, key=f"comp_{artist_name}"
    )
    lyric_sel = exp.multiselect(
        "Авторы текста", person_names, default=lyric_default, key=f"lyric_{artist_name}"
    )
    presets_ui[artist_name] = {
        "label_id": config["labels"][p_label],
        "genre_id": p_genre,
        "recording_year": p_year,
        "language_id": p_lang,
        "composers": [persons[n] for n in comp_sel if n in persons],
        "lyricists": [persons[n] for n in lyric_sel if n in persons],
    }
config["presets"] = presets_ui

if st.sidebar.button("Сохранить конфиг", key="save_config"):
    save_config(config)
    st.sidebar.success("Конфигурация сохранена")

max_workers = st.sidebar.number_input(
    "Параллельные загрузки", min_value=1, max_value=5, value=1, step=1, key="workers"
)

# —————————————
# Main UI
# —————————————
st.title("Массовая загрузка релизов")
st.markdown("Перетащите файлы PNG (обложки) и WAV (аудио):")


covers = st.file_uploader("Обложки (PNG)", type=["png"], accept_multiple_files=True)
wavs = st.file_uploader("Аудио (WAV)", type=["wav"], accept_multiple_files=True)

# Group files by base name
groups: dict[str, dict[str, UploadedFile]] = {}
for f in covers:
    groups.setdefault(Path(f.name).stem, {})["cover"] = f
for f in wavs:
    groups.setdefault(Path(f.name).stem, {})["audio"] = f

st.write("Найденные релизы:")

found = []
for base, files in groups.items():
    title_part = base.split(" - ", 1)[1] if " - " in base else base
    ver = ""
    m = re.search(r"\(([^()]*)\)\s*$", title_part)
    if m:
        ver = m.group(1).strip()
        title_part = title_part[: m.start()].rstrip()
    found.append(
        {
            "Файл": base,
            "Артист": base.split(" - ", 1)[0] if " - " in base else "",
            "Название": title_part,
            "Версия": ver,
            "Обложка": "✅" if "cover" in files else "⚠️",
            "Аудио": "✅" if "audio" in files else "⚠️",
        }
    )
st.table(found)

track_settings = {}
for base, files in groups.items():
    artist = base.split(" - ", 1)[0] if " - " in base else base
    with st.expander(base, expanded=False):
        p_exp = st.checkbox("Ненормативная лексика", value=False, key=f"ex_{base}")
        p_date = st.date_input("Дата трека", value=date.today(), key=f"td_{base}")
    track_settings[base] = {"explicit": p_exp, "track_date": p_date.isoformat()}


def batch_update_tracks(release_id, track_list, sess):
    st.write("→ Обновление метаданных трека…")
    for meta in track_list:
        tid = meta.get("trackId")
        data = {k: v for k, v in meta.items() if k != "trackId"}
        r = sess.put(
            f"https://v2api.musicalligator.com/api/releases/{release_id}/tracks/{tid}",
            json=data,
        )
        st.write(f"Обновление трека {tid}: {r.status_code}")
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
    st.write("→ Установка лейбла…")
    r = sess.put(
        f"https://v2api.musicalligator.com/api/releases/{release_id}",
        json=data,
    )
    st.write(f"Ответ на изменение лейбла: {r.status_code}")
    if r.status_code >= 400:
        st.write(r.text)


def set_streaming_platforms(release_id: int, platforms: list[int], sess):
    data = {"streamingPlatforms": platforms}
    st.write("→ Установка площадок…")
    r = sess.put(
        f"https://v2api.musicalligator.com/api/releases/{release_id}",
        json=data,
    )
    st.write(f"Ответ на изменение площадок: {r.status_code}")
    if r.status_code >= 400:
        st.write(r.text)


def upload_release(base, files, opts):
    local = client.clone_session()
    artist, title = (base.split(" - ", 1) + [""])[:2]
    version = ""
    m = re.search(r"\(([^()]*)\)\s*$", title)
    if m:
        version = m.group(1).strip()
        title = title[: m.start()].rstrip()
    if artist not in config["artists"]:
        st.error(f"Нет artist_id для '{artist}'")
        return
    preset = config["presets"][artist]
    main_genre = preset.get("genre_id")
    artist_id = config["artists"][artist]

    # 1) Создать черновик
    st.write(f"→ Создание черновика для '{title}'…")
    r1 = local.post(
        "https://v2api.musicalligator.com/api/releases/create",
        json={"releaseType": "SINGLE"},
    )
    if r1.status_code != 201:
        st.error(f"Ошибка создания: {r1.status_code} {r1.text}")
        return
    rid = r1.json()["data"]["release"]["releaseId"]
    st.write(f"Черновик {rid} создан")

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
        "genre": {"genreId": main_genre},
        "tracks": [{"trackId": track0}],
        "countries": [],
    }
    if version:
        meta_release["releaseVersion"] = version
    r2 = local.put(
        f"https://v2api.musicalligator.com/api/releases/{rid}", json=meta_release
    )
    st.write(f"Метаданные обновлены: {r2.status_code}")
    if r2.status_code >= 400:
        st.write(r2.text)

    # 2a) Установить лейбл
    label_id = preset.get("label_id")
    if label_id:
        year = date.fromisoformat(track_date).year
        set_release_label(rid, label_id, year, local)

    # 3) Upload cover
    if "cover" in files:
        st.write("→ Загрузка обложки…")
        r3 = local.post(
            f"https://v2api.musicalligator.com/api/releases/{rid}/cover",
            files={"file": (files["cover"].name, files["cover"], "image/png")},
        )
        st.write(f"Ответ загрузки обложки: {r3.status_code}")
        if r3.status_code >= 400:
            st.write(r3.text)

    # 4) Upload audio на правильный endpoint
    if "audio" in files:
        st.write("→ Загрузка аудио…")
        fa = files["audio"]
        r4 = local.post(
            f"https://v2api.musicalligator.com/api/releases/{rid}/tracks/{track0}/upload",
            files={"file": (fa.name, fa, "audio/wav")},
        )
        st.write(f"Ответ загрузки аудио: {r4.status_code}")
        if r4.status_code not in (200, 201):
            st.error("Не удалось загрузить аудио")
            st.write(r4.text)
            return

        # 5) Обновить метаданные трека
        if not preset.get("composers") or not preset.get("lyricists"):
            st.warning(f"Отсутствуют композиторы/авторы текста для {artist}")
        st.write("→ Подготовка метаданных трека…")
        persons = [{"id": c, "role": "MUSIC_AUTHOR"} for c in preset["composers"]] + [
            {"id": l, "role": "LYRICS_AUTHOR"} for l in preset["lyricists"]
        ]
        track_meta = {
            "trackId": track0,
            "artist": artist_id,
            "artists": [{"id": artist_id, "role": "MAIN"}],
            "title": title,
            "trackVersion": version if version else None,
            "genre": {"genreId": main_genre},
            "recordingYear": preset["recording_year"],
            "language": preset["language_id"],
            "composers": preset["composers"],
            "lyricists": preset["lyricists"],
            "persons": persons,
            "adult": opts.get("explicit", False),
            "trackDate": opts.get("track_date"),
        }
        if track_meta["trackVersion"] is None:
            del track_meta["trackVersion"]

        track_list.append(track_meta)

    if track_list:
        batch_update_tracks(rid, track_list, local)

    set_streaming_platforms(
        rid,
        config.get("streaming_platforms", [195, 196, 197]),
        local,
    )

    st.success(f"Релиз {rid} готов!")
    st.markdown(f"[Открыть релиз](https://app.musicalligator.ru/releases/{rid})")


def run_all_uploads():
    total = len(groups)
    progress = st.progress(0.0)
    done = 0
    futures = []
    with ThreadPoolExecutor(max_workers=max_workers) as exe:
        for base, files in groups.items():
            opts = track_settings.get(base, {})
            futures.append(exe.submit(run_with_ctx, upload_release, base, files, opts))
        for _ in as_completed(futures):
            done += 1
            progress.progress(done / total)
    st.balloons()
    st.session_state.upload_done = True


if "upload_done" not in st.session_state:
    st.session_state.upload_done = False

if not st.session_state.upload_done:
    if st.button("Запустить загрузку", key="upload_button"):
        run_all_uploads()
else:
    if st.button("Загрузить ещё", key="upload_more"):
        st.session_state.upload_done = False
        st.experimental_rerun()
