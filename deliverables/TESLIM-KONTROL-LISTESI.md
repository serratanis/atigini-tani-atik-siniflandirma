# Atığını Tanı — Teslim Kontrol Listesi

## Yönerge kapsamı

- [x] Gerçek dünya problemi, girdi ve hedef sınıflar açıklandı.
- [x] Veri kaynağı, DOI, görüntü sayısı, çözünürlük ve dokuz sınıfın dağılımı verildi.
- [x] UCI ile yazar deposu arasındaki lisans farkı açıklandı; daha kısıtlayıcı koşul esas alındı.
- [x] Sınıf dağılımı, örnek görüntü ızgarası ve parlaklık dağılımı üretildi.
- [x] Yeniden boyutlandırma, normalizasyon, artırma, stratified bölme ve sınıf ağırlığı açıklandı.
- [x] 4.752 dosyada SHA-256 tam kopya denetimi yapıldı; kopya bulunmadı.
- [x] ImageNet-1k ön-eğitimli MobileNetV2 mimarisi ve seçim gerekçesi açıklandı.
- [x] Eğitim ayarları, seed, validation takibi ve model seçimi belgelendi.
- [x] Accuracy, macro precision/recall/F1, weighted metrikler, top-2 accuracy ve baseline raporlandı.
- [x] Normalize confusion matrix, sınıf bazlı rapor ve yüksek güvenli yanlış tahmin galerisi üretildi.
- [x] Güçlü yönler, zayıf sınıflar, dış doğrulama sınırı ve geliştirme önerileri tartışıldı.
- [x] Beş sayfalık DOCX ve PDF rapor hazırlandı ve görsel olarak denetlendi.
- [x] Colab uyumlu notebook, test tahminleri CSV'si, metrik JSON'u ve eğitilmiş model pakete eklendi.
- [x] Fotoğraf yüklemeli Streamlit arayüzü hazırlandı.

## Doğrulanmış sonuçlar

- Test örneği: 713
- Accuracy: %84,85
- Macro precision: %84,78
- Macro recall: %87,18
- Macro F1: %85,54
- Top-2 accuracy: %94,39
- Çoğunluk sınıfı baseline: %19,38
- En güçlü F1: Vegetation %92,65
- Ana iyileştirme alanları: Miscellaneous Trash %74,51; Plastic %77,97

## Yayın bağlantıları

- [x] Public GitHub deposu: <https://github.com/serratanis/atigini-tani-atik-siniflandirma>
- [x] Google Colab çalışma defteri: <https://colab.research.google.com/github/serratanis/atigini-tani-atik-siniflandirma/blob/main/notebooks/Atigini_Tani_RealWaste.ipynb>

Ham RealWaste görüntüleri lisans ve paket boyutu nedeniyle teslim ZIP'ine eklenmez. Veri, `bash scripts/download_data.sh` komutuyla resmî yazar deposundan yeniden indirilebilir.
