# Atığını Tanı — Gerçek Ortam Atık Görüntülerinin Sınıflandırılması

Atığını Tanı, gerçek bir depolama sahasında çekilmiş atık görüntülerini dokuz malzeme sınıfından birine ayıran derin öğrenme projesidir. Çalışma yalnızca toplam doğruluğu değil; sınıf dengesi, macro precision–recall–F1, confusion matrix ve yanlış tahmin örneklerini birlikte değerlendirir.

## Problem

Girdi, tek bir RGB atık görüntüsüdür. Hedef; görüntüyü `Cardboard`, `Food Organics`, `Glass`, `Metal`, `Miscellaneous Trash`, `Paper`, `Plastic`, `Textile Trash` veya `Vegetation` sınıfına atamaktır. Böyle bir karar desteği, ayrıştırma hattında insan kontrolünü destekleyebilir; ancak proje modeli gerçek bir tesis kontrol sistemi olarak sunmaz.

## Veri seti

- **Ad:** RealWaste
- **Kaynak:** UCI Machine Learning Repository
- **DOI:** [10.24432/C5SS4G](https://doi.org/10.24432/C5SS4G)
- **Boyut:** 4.752 görüntü, 9 sınıf, 524 × 524 piksel
- **Ortam:** Gerçek depolama sahası
- **Lisans:** UCI kaydı CC BY 4.0, yazar deposu CC BY-NC-SA 4.0 belirtir; proje daha kısıtlayıcı CC BY-NC-SA 4.0 koşullarını esas alır
- **Veri sayfası:** [UCI RealWaste](https://archive.ics.uci.edu/dataset/908/realwaste)
- **Yazar deposu:** [sam-single/realwaste](https://github.com/sam-single/realwaste)

## Yöntem

- Stratified %70 eğitim, %15 validation ve %15 test ayrımı
- Bölme öncesi SHA-256 ile tam kopya denetimi; kopya bulunursa eğitim güvenli biçimde durur
- Yalnızca eğitim verisine yatay çevirme, küçük döndürme ve sınırlı parlaklık/kontrast artırımı
- Sınıf dengesizliği için ağırlıklı cross-entropy
- ImageNet-1k üzerinde önceden eğitilmiş [`google/mobilenet_v2_1.0_224`](https://huggingface.co/google/mobilenet_v2_1.0_224) ile transfer learning
- AdamW, düşük learning rate, validation loss tabanlı azaltma ve early stopping
- Accuracy, macro/weighted precision–recall–F1, top-2 accuracy ve confusion matrix

## Çalıştırma

İlk kurulumda:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
bash scripts/download_data.sh
```

Hazır eğitilmiş modelle görsel arayüzü açmak için ham veri indirmek gerekmez:

```bash
streamlit run app.py
```

Modeli veriden yeniden eğitmek için:

```bash
python src/train_model.py --data-dir data/raw/realwaste-main/RealWaste
```

Komut; veri bölme kaydını, üç keşif görselini, eğitim eğrilerini, confusion matrix'i, hata galerisini, sınıf bazlı metrikleri, satır düzeyinde test tahminlerini ve en iyi model ağırlıklarını üretir.

## Doğrulanmış final sonucu

- Test seti: 713 görüntü
- Accuracy: **%84,85**
- Macro precision / recall / F1: **%84,78 / %87,18 / %85,54**
- Top-2 accuracy: **%94,39**
- Çoğunluk sınıfı baseline: **%19,38**
- Model: 2.235.401 parametreli MobileNetV2, 4 doğrulanmış fine-tuning epoch'u

Tüm sınıf metrikleri, confusion matrix ve hata analizi `deliverables/Atigini-Tani-Proje-Raporu.pdf` içinde yer alır.

## Teslim yapısı

```text
data/          Veri lisansı, kaynak kaydı ve bölme manifesti
deliverables/  3–5 sayfalık proje raporu ve teslim kontrol listesi
figures/       EDA, eğitim, confusion matrix ve hata analizi görselleri
models/        En iyi model ağırlıkları
notebooks/     Colab uyumlu uçtan uca çalışma
results/       Metrikler ve yeniden üretilebilirlik kaydı
src/           Eğitim, değerlendirme ve tahmin kodu
```

## Sınırlar

Bu model, RealWaste veri dağılımı üzerinde bir eğitim projesidir. Farklı kamera, ışık, coğrafya veya belediye ayrıştırma kurallarında performans düşebilir. Tahmin, yerel atık mevzuatının veya insan denetiminin yerine geçmez.
