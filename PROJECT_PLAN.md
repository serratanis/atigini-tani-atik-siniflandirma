# Atığını Tanı — Yönerge Eşleştirmesi

## 3.1 Problem tanımı

RGB atık görüntüsünden dokuz malzeme sınıfını tahmin etmek; gerçek ayrıştırma ortamında karar desteği sağlamak. Girdi görüntü, hedef sınıf etiketi, gerçek dünya ihtiyacı doğru ayrıştırmayı desteklemektir.

## 3.2 Veri seti

UCI RealWaste; 4.752 görüntü, 9 sınıf, gerçek depolama sahası, DOI 10.24432/C5SS4G. UCI lisans kaydı CC BY 4.0, yazar deposu CC BY-NC-SA 4.0 belirttiği için proje daha kısıtlayıcı koşulu esas alır. Sınıf dağılımı raporda açıkça verilecek.

## 3.3 Veri keşfi

1. Sınıf dağılımı
2. Her sınıftan örnek görüntü ızgarası
3. Sınıflara göre parlaklık dağılımı

## 3.4 Ön işleme

- RGB dönüşümü ve 224 × 224 yeniden boyutlandırma
- MobileNetV2 ön işleyicisiyle uyumlu `[-1, 1]` kanal normalizasyonu
- Yalnızca eğitim verisine yatay çevirme, ±12° döndürme, sınırlı parlaklık/kontrast değişimi
- Stratified %70/%15/%15 ayrım
- Bölme öncesinde SHA-256 tam kopya denetimi; veri sızıntısı varsa eğitim durdurulur
- Sınıf ağırlıklı kayıp fonksiyonu

## 3.5 Model

ImageNet-1k üzerinde önceden eğitilmiş MobileNetV2 omurgası ve RealWaste için yeniden başlatılan dokuz sınıflı çıktı katmanı. Derinlik-ayrılabilir evrişimler ve ters artık blokları sayesinde taşınabilir bir mimari. Tüm katmanlar düşük learning rate ile birlikte ince ayarlanır. Loss: weighted cross-entropy. Optimizer: AdamW.

## 3.6 Eğitim

En çok 12 epoch, batch size 32, başlangıç learning rate 1e-4, ReduceLROnPlateau ve validation loss tabanlı early stopping. Sabit seed: 42.

## 3.7 Değerlendirme

Accuracy, macro ve weighted precision/recall/F1, top-2 accuracy, majority baseline, sınıf bazlı rapor ve normalize confusion matrix.

## 3.8 Hata analizi

En güvenli yanlış tahminlerden 12 örnek, en sık karışan sınıf çiftleri, ışık/arka plan/örtüşme etkileri, veri dağılımı ve saha genellenebilirliği sınırlamaları.

## Teslim

- 3–5 sayfalık profesyonel rapor
- Rapor içinde veri kaynağı/DOI ve GitHub/Colab bağlantı alanı
- Altı kanıt görseli
- Metrik JSON'u ve sınıf bazlı sonuçlar
- Colab uyumlu notebook
- Eğitilmiş model ve tek görüntü tahmin aracı
