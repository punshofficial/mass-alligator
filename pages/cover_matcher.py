from __future__ import annotations

import io
from pathlib import Path
from typing import Dict, Optional

import numpy as np
import streamlit as st
import yaml
from PIL import Image

CONFIG_FILE = Path("cover_config.yaml")
DEFAULT_CONFIG = {
    "output_dir": "covers_output",
    "blend_mode": "overlay",
    "opacity": 24,
    "texture_path": None,
}


def load_config() -> dict:
    if CONFIG_FILE.exists():
        with CONFIG_FILE.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f) or DEFAULT_CONFIG.copy()
    CONFIG_FILE.write_text(yaml.safe_dump(DEFAULT_CONFIG), encoding="utf-8")
    return DEFAULT_CONFIG.copy()


def save_config(cfg: dict) -> None:
    CONFIG_FILE.write_text(yaml.safe_dump(cfg), encoding="utf-8")


config: Dict[str, Optional[str | int]] = load_config()

st.set_page_config(page_title="Batch Cover Matcher", layout="wide")
st.title("🎧 Batch Cover Matcher for EDM Covers")

with st.sidebar:
    st.header("⚙️ Настройки")

    texture_path: Optional[str] = None
    if config.get("texture_path") and Path(config["texture_path"]).exists():
        st.text("Текущая текстура:")
        st.image(config["texture_path"], width=100)
        if st.button("Заменить текстуру"):
            config["texture_path"] = None
            save_config(config)
        else:
            texture_path = config["texture_path"]
    if texture_path is None:
        uploaded_tex = st.file_uploader(
            "Загрузить текстуру (PNG/JPG)", type=["png", "jpg", "jpeg"]
        )
        if uploaded_tex:
            tex_dir = Path("textures")
            tex_dir.mkdir(exist_ok=True)
            path = tex_dir / uploaded_tex.name
            path.write_bytes(uploaded_tex.read())
            config["texture_path"] = str(path)
            save_config(config)
            texture_path = str(path)

    modes = ["overlay", "multiply", "screen"]
    config["blend_mode"] = st.selectbox(
        "Режим наложения", modes, index=modes.index(config.get("blend_mode", "overlay"))
    )
    config["opacity"] = st.slider(
        "Непрозрачность (%)", 0, 100, int(config.get("opacity", 24))
    )

    st.markdown("---")
    dirs = [d for d in Path(".").iterdir() if d.is_dir()]
    dir_names = ["<Создать новую>"] + [d.name for d in dirs]
    current = config.get("output_dir", "covers_output")
    idx = dir_names.index(current) if current in dir_names else 0
    sel = st.selectbox("Папка для сохранения", dir_names, index=idx)
    if sel == "<Создать новую>":
        config["output_dir"] = st.text_input("Имя новой папки", value=current)
    else:
        config["output_dir"] = sel
    save_config(config)

wavs = st.file_uploader(
    "1) Загрузите WAV-файлы", type=["wav"], accept_multiple_files=True
)
if not wavs:
    st.info("Загрузите WAV-файлы для начала")
    st.stop()

st.subheader("2) Добавьте обложки к трекам")
cover_data: Dict[str, bytes] = {}
for wav in wavs:
    with st.expander(wav.name, expanded=False):
        file = st.file_uploader(
            f"Обложка для {wav.name}", type=["png", "jpg", "jpeg"], key=wav.name
        )
        if file:
            data = file.read()
            img = Image.open(io.BytesIO(data))
            st.image(img, width=120)
            cover_data[wav.name] = data

if st.button("▶️ Run"):
    missing = [w.name for w in wavs if w.name not in cover_data]
    if missing:
        st.error(f"Нет обложек для: {', '.join(missing)}")
        st.stop()

    out_dir = Path(config["output_dir"])
    out_dir.mkdir(exist_ok=True)
    target = 3000

    texture_arr = None
    if texture_path:
        tex_img = (
            Image.open(texture_path)
            .convert("RGB")
            .resize((target, target), Image.LANCZOS)
        )
        texture_arr = np.array(tex_img).astype(np.float32)

    results = []
    for wav in wavs:
        base = Path(wav.name).stem
        img = Image.open(io.BytesIO(cover_data[wav.name])).convert("RGB")
        w, h = img.size
        scale = max(target / w, target / h)
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
        w2, h2 = img.size
        left, top = (w2 - target) // 2, (h2 - target) // 2
        img = img.crop((left, top, left + target, top + target))

        if texture_arr is not None:
            base_arr = np.array(img).astype(np.float32)
            if config["blend_mode"] == "overlay":
                mask = base_arr <= 128
                blended = np.zeros_like(base_arr)
                blended[mask] = 2 * base_arr[mask] * texture_arr[mask] / 255
                blended[~mask] = (
                    255 - 2 * (255 - base_arr[~mask]) * (255 - texture_arr[~mask]) / 255
                )
            elif config["blend_mode"] == "multiply":
                blended = base_arr * texture_arr / 255
            else:
                blended = 255 - (255 - base_arr) * (255 - texture_arr) / 255
            alpha = int(config["opacity"]) / 100.0
            result_arr = (1 - alpha) * base_arr + alpha * blended
            result_arr = np.clip(result_arr, 0, 255).astype(np.uint8)
            img = Image.fromarray(result_arr)

        out_path = out_dir / f"{base}.png"
        img.save(out_path)
        results.append(str(out_path))

    st.success(f"Готово! Сохранено {len(results)} обложек в '{out_dir}'")
    st.write(results)
