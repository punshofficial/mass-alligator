import streamlit as st
from PIL import Image
import io, os
import yaml
import numpy as np

# --- Константы и конфиг ---
CONFIG_FILE = "config.yaml"
DEFAULT_CONFIG = {
    "output_dir": "covers_output",
    "blend_mode": "overlay",
    "opacity": 24,
    "texture_path": None
}

# Загрузка/инициализация конфига
def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return yaml.safe_load(f) or DEFAULT_CONFIG.copy()
    else:
        with open(CONFIG_FILE, "w") as f:
            yaml.safe_dump(DEFAULT_CONFIG, f)
        return DEFAULT_CONFIG.copy()

config = load_config()

def save_config():
    with open(CONFIG_FILE, "w") as f:
        yaml.safe_dump(config, f)

# --- UI Streamlit ---
st.set_page_config(page_title="Batch Cover Matcher", layout="wide")
st.title("🎧 Batch Cover Matcher for EDM Covers")

# Sidebar settings
with st.sidebar:
    st.header("⚙️ Настройки")

    # Texture loading or existing texture
    texture = None
    if config.get("texture_path") and os.path.exists(config["texture_path"]):
        st.text("Текущая текстура:")
        st.image(config["texture_path"], width=100)
        if st.button("Заменить текстуру"):
            config["texture_path"] = None
            save_config()
        else:
            texture = config["texture_path"]
    if texture is None:
        uploaded_tex = st.file_uploader("Загрузить текстуру (PNG/JPG)", type=["png","jpg","jpeg"])
        if uploaded_tex:
            os.makedirs("textures", exist_ok=True)
            path = os.path.join("textures", uploaded_tex.name)
            with open(path, "wb") as f:
                f.write(uploaded_tex.read())
            config["texture_path"] = path
            save_config()
            texture = path

    # Blend mode and opacity
    config["blend_mode"] = st.selectbox(
        "Режим наложения",
        ["overlay","multiply","screen"],
        index=["overlay","multiply","screen"].index(config.get("blend_mode","overlay"))
    )
    config["opacity"] = st.slider("Непрозрачность (%)", 0, 100, config.get("opacity",24))

    # Output directory
    st.markdown("---")
    dirs = [d for d in os.listdir() if os.path.isdir(d)]
    dirs.insert(0, "<Создать новую>")
    sel = st.selectbox("Папка для сохранения", dirs,
                       index=dirs.index(config.get("output_dir")) if config.get("output_dir") in dirs else 0)
    if sel == "<Создать новую>":
        config["output_dir"] = st.text_input("Имя новой папки", value=config.get("output_dir"))
    else:
        config["output_dir"] = sel

    save_config()

# 1) Загрузка WAV-файлов
wavs = st.file_uploader("1) Загрузите WAV-файлы", type=["wav"], accept_multiple_files=True)
if not wavs:
    st.info("Загрузите WAV-файлы для начала")
    st.stop()

# 2) Добавление обложек
st.subheader("2) Добавьте обложки к трекам")
cover_data = {}
for wav in wavs:
    with st.expander(wav.name, expanded=False):
        f = st.file_uploader(f"Обложка для {wav.name}", type=["png","jpg","jpeg"], key=wav.name)
        if f:
            data = f.read()
            img = Image.open(io.BytesIO(data))
            st.image(img, width=120)
            cover_data[wav.name] = data

# 3) Запуск обработки
if st.button("▶️ Run"):
    missing = [w.name for w in wavs if w.name not in cover_data]
    if missing:
        st.error(f"Нет обложек для: {', '.join(missing)}")
        st.stop()

    out_dir = config["output_dir"]
    os.makedirs(out_dir, exist_ok=True)
    TARGET = 3000

    # Загрузка текстуры
    texture_arr = None
    if config.get("texture_path"):
        tex_img = Image.open(config["texture_path"]).convert("RGB").resize((TARGET, TARGET), Image.LANCZOS)
        texture_arr = np.array(tex_img).astype(np.float32)

    results = []
    for wav in wavs:
        base = os.path.splitext(wav.name)[0]
        img = Image.open(io.BytesIO(cover_data[wav.name])).convert("RGB")
        # Resize & center crop
        w, h = img.size
        scale = max(TARGET/w, TARGET/h)
        img = img.resize((int(w*scale), int(h*scale)), Image.LANCZOS)
        w2, h2 = img.size
        left, top = (w2 - TARGET)//2, (h2 - TARGET)//2
        img = img.crop((left, top, left+TARGET, top+TARGET))

        # Blending with texture
        if texture_arr is not None:
            base_arr = np.array(img).astype(np.float32)
            # select blend mode
            if config["blend_mode"] == "overlay":
                mask = base_arr <= 128
                blended = np.zeros_like(base_arr)
                blended[mask] = (2 * base_arr[mask] * texture_arr[mask] / 255)
                blended[~mask] = (255 - 2 * (255 - base_arr[~mask]) * (255 - texture_arr[~mask]) / 255)
            elif config["blend_mode"] == "multiply":
                blended = base_arr * texture_arr / 255
            else:  # screen
                blended = 255 - (255 - base_arr) * (255 - texture_arr) / 255
            alpha = config["opacity"] / 100.0
            result_arr = (1 - alpha) * base_arr + alpha * blended
            result_arr = np.clip(result_arr, 0, 255).astype(np.uint8)
            img = Image.fromarray(result_arr)

        out_path = os.path.join(out_dir, f"{base}.png")
        img.save(out_path)
        results.append(out_path)

    st.success(f"Готово! Сохранено {len(results)} обложек в '{out_dir}'")
    st.write(results)