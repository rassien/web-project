<<<<<<< HEAD
# calisan-sube-eslestirme
=======
# Banka Şube Eşleştirme Sistemi

Bu proje, verilen bir ev adresine en yakın banka şubelerini bulan bir API sistemidir.

## Özellikler

- Adres bazlı en yakın 5 şubeyi bulma
- Mesafe hesaplama (km cinsinden)
- Şube ekleme ve yönetimi
- Geocoding desteği

## Kurulum

1. Gerekli paketleri yükleyin:
```bash
pip install -r requirements.txt
```

2. Uygulamayı başlatın:
```bash
python main.py
```

## API Kullanımı

### En Yakın Şubeleri Bulma

```bash
POST /en-yakin-subeler/
{
    "adres": "Örnek Mahallesi, Örnek Sokak No:1, İstanbul"
}
```

### Yeni Şube Ekleme

```bash
POST /sube-ekle/
{
    "id": 1,
    "ad": "Merkez Şube",
    "adres": "Örnek Mahallesi, Örnek Sokak No:1, İstanbul"
}
```

## Notlar

- Sistem Nominatim geocoding servisini kullanmaktadır
- Mesafeler kuş uçuşu olarak hesaplanmaktadır
- Tüm mesafeler kilometre cinsindendir 
>>>>>>> 6d795b7e (İlk commit)
