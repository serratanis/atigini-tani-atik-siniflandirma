from __future__ import annotations

from pathlib import Path
import sys

import numpy as np
from PIL import Image
import streamlit as st
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from train_model import IMAGE_MEAN, IMAGE_STD, load_trained_model  # noqa: E402


PROJECT = Path(__file__).resolve().parent
MODEL_PATH = PROJECT / "models" / "atigini-tani-mobilenetv2.pt"

TR_LABELS = {
    "Cardboard": "Karton",
    "Food Organics": "Gıda organiği",
    "Glass": "Cam",
    "Metal": "Metal",
    "Miscellaneous Trash": "Karışık atık",
    "Paper": "Kâğıt",
    "Plastic": "Plastik",
    "Textile Trash": "Tekstil atığı",
    "Vegetation": "Bitkisel atık",
}


st.set_page_config(page_title="Atığını Tanı", page_icon="♻️", layout="wide")
st.markdown(
    """
    <style>
      .stApp { background: #f5f0e6; color: #20332e; }
      [data-testid="stHeader"] { background: transparent; }
      .hero { background: #173f3a; color: white; padding: 2rem; border-radius: 24px; margin-bottom: 1.2rem; }
      .hero small { color: #a7c4a0; letter-spacing: .1em; font-weight: 700; }
      .hero h1 { margin: .4rem 0; font-size: 3rem; }
      .hero p { color: #f5f0e6; max-width: 48rem; }
      .note { background: #eaf0ea; border-left: 5px solid #e76f51; padding: 1rem; border-radius: 12px; }
      div[data-testid="stMetric"] { background: white; padding: 1rem; border: 1px solid #d4ddd8; border-radius: 16px; }
    </style>
    <div class="hero">
      <small>GERÇEK ORTAM GÖRÜNTÜ SINIFLANDIRMA</small>
      <h1>Atığını Tanı</h1>
      <p>Bir atık fotoğrafı yükle; model dokuz malzeme sınıfı arasından en olası üç sonucu ve güven dağılımını göstersin.</p>
    </div>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource
def load_model():
    checkpoint = torch.load(MODEL_PATH, map_location="cpu", weights_only=True)
    classes = checkpoint["class_names"]
    model = load_trained_model(checkpoint, torch.device("cpu"))
    return model, classes, int(checkpoint["image_size"])


def prepare(image: Image.Image, image_size: int) -> torch.Tensor:
    image = image.convert("RGB").resize((image_size, image_size), Image.Resampling.BILINEAR)
    array = np.asarray(image, dtype=np.float32) / 255.0
    array = (array - IMAGE_MEAN) / IMAGE_STD
    return torch.from_numpy(array.transpose(2, 0, 1).copy()).unsqueeze(0)


left, right = st.columns([1.05, 1], gap="large")
with left:
    uploaded = st.file_uploader("Atık fotoğrafı yükle", type=["jpg", "jpeg", "png"])
    if uploaded:
        image = Image.open(uploaded)
        st.image(image, caption="Yüklenen görüntü", use_container_width=True)
    else:
        st.info("Tahmin için JPG veya PNG biçiminde bir fotoğraf seç.")

with right:
    if not MODEL_PATH.exists():
        st.error("Model dosyası bulunamadı. Önce eğitim akışını çalıştırın.")
    elif uploaded:
        model, classes, image_size = load_model()
        with torch.inference_mode():
            probabilities = torch.softmax(model(prepare(image, image_size)), dim=1)[0]
        values, indices = probabilities.topk(k=3)
        st.subheader("En olası sonuçlar")
        for rank, (value, index) in enumerate(zip(values.tolist(), indices.tolist()), start=1):
            label = TR_LABELS.get(classes[index], classes[index])
            st.metric(f"{rank}. {label}", f"%{value * 100:.1f}")
            st.progress(float(value))
        if float(values[0]) < 0.55:
            st.warning("Modelin güveni düşük. Bu örnek insan kontrolüne yönlendirilmelidir.")
        st.markdown(
            '<div class="note"><b>Önemli:</b> Bu sonuç eğitim amaçlı karar desteğidir. Yerel ayrıştırma kuralları ve insan kontrolü önceliklidir.</div>',
            unsafe_allow_html=True,
        )
    else:
        st.subheader("Model ne yapıyor?")
        st.write("Görüntüyü 224 × 224 boyutuna getirir; ImageNet üzerinde önceden eğitilmiş MobileNetV2 ile özellik çıkarır ve dokuz sınıf için olasılık üretir.")
        st.caption("RealWaste • 4.752 görüntü • 9 sınıf • ham veri teslim paketine dahil değildir")

st.divider()
st.caption("Atığını Tanı — TNC Group Makine ve Derin Öğrenme Uygulamaları Final Projesi")
