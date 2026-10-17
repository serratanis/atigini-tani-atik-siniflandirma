# Veri Kaydı

## RealWaste

- UCI kayıt numarası: 908
- DOI: 10.24432/C5SS4G
- Kaynak: https://archive.ics.uci.edu/dataset/908/realwaste
- İndirme: https://archive.ics.uci.edu/static/public/908/realwaste.zip
- Lisans kaydı: UCI atıf metni `CC BY 4.0`; veri seti yazarının resmî GitHub README'si `CC BY-NC-SA 4.0` belirtir.
- Proje uyumu: Çelişki nedeniyle daha kısıtlayıcı `CC BY-NC-SA 4.0` koşulları esas alınır; ham görüntüler teslim paketine eklenmez.
- Atıf: Single, S., Iranmanesh, S., & Raad, R. (2023). RealWaste [Dataset]. UCI Machine Learning Repository.
- Yazar deposu: https://github.com/sam-single/realwaste

Ham görüntüler boyut ve lisans takibi nedeniyle proje Git deposuna ve teslim ZIP'ine eklenmez. `bash scripts/download_data.sh` komutu yazarın resmî GitHub ağacını okur, görüntüleri paralel ve dosya bazında devam ettirilebilir biçimde indirir; eğitim kodu veri klasörünü `data/raw/realwaste-main/RealWaste` altında bekler. İndirici kaynak ağacının SHA değerini ham veri klasörüne kaydeder; final deneyinde kullanılan aynı kayıt ayrıca sürüm kontrollü `data/source-integrity.json` dosyasındadır.

## Sınıflar ve resmî örnek sayıları

- Cardboard: 461
- Food Organics: 411
- Glass: 420
- Metal: 790
- Miscellaneous Trash: 495
- Paper: 500
- Plastic: 921
- Textile Trash: 318
- Vegetation: 436

Toplam: 4.752 görüntü.
