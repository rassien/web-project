
# Proje: Çalışan Şube Eşleştirme ve Atama Sistemi

Bu proje, çalışan adreslerine en yakın banka şubelerini bularak verimli bir şekilde atama yapılmasını sağlayan bir web uygulamasıdır. Google Haritalar API'si ile entegre çalışarak mesafe, süre ve toplu taşıma bilgilerini analiz eder ve kullanıcı dostu bir arayüzde sunar.

## Temel Özellikler

- **Kullanıcı Yönetimi:** Kayıt olma ve giriş yapma işlevselliği ile güvenli bir kullanım sunar.
- **Tekli ve Toplu Analiz:**
    - **Tek Adres Analizi:** Belirli bir çalışanın adresine göre en yakın şubeleri listeler.
    - **Toplu Analiz:** Excel dosyası üzerinden birden çok çalışanın ve şubenin verisini alarak toplu eşleştirme yapar.
- **Gelişmiş Filtreleme:**
    - Maksimum mesafe (km) ve bulunacak şube sayısı gibi parametrelerle analizi özelleştirme imkanı.
- **Etkileşimli Harita:** Analiz sonuçlarını (çalışan ve şube konumlarını) interaktif bir harita üzerinde gösterir.
- **Atama Yönetimi:**
    - Analiz sonuçlarına göre çalışanları şubelere atama.
    - Yapılan atamaları ayrı bir sayfada listeleme, düzenleme, silme ve Excel'e aktarma.
    - Şube "norm" (kadro) takibi yaparak atamalara göre otomatik güncelleme.
- **Toplu Taşıma Rotaları:** Seçilen çalışan ve şube arasında toplu taşıma alternatiflerini ve yolculuk adımlarını gösterir.
- **Veri İndirme:** Tüm analiz ve atama sonuçlarını Excel (.xlsx) formatında indirme imkanı.
- **Önbellekleme (Caching):** Adres koordinatlarını `adres_cache.json` dosyasında saklayarak API çağrılarını optimize eder ve performansı artırır.

## Teknolojiler ve Kütüphaneler

- **Backend:** Python, Flask
- **Frontend:** HTML, Bootstrap 5, JavaScript
- **Veri İşleme ve API'ler:**
    - **Pandas:** Excel dosyalarını okuma ve işleme.
    - **Geopy & Google Maps API:** Adresleri coğrafi koordinatlara çevirme (Geocoding) ve şubeler arası mesafe/süre hesaplama.
    - **Requests:** Google Maps API'lerine HTTP istekleri gönderme.
- **Veritabanı/Depolama:**
    - Kullanıcı bilgileri için `users.xlsx`.
    - Atama kayıtları için `assignments.xlsx`.
- **Diğer Kütüphaneler:**
    - **Flask-Login:** Kullanıcı oturum yönetimi.
    - **python-dotenv:** API anahtarı gibi hassas bilgileri güvenli bir şekilde saklama.
    - **XlsxWriter:** Excel dosyaları oluşturma.
    - **Leaflet.js:** İnteraktif harita gösterimi.

## Proje Yapısı

- `main.py`: Ana Flask uygulamasını ve tüm backend mantığını içerir. API endpoint'leri burada tanımlanmıştır.
- `templates/`: Kullanıcı arayüzünü oluşturan HTML dosyalarını barındırır.
    - `index.html`: Ana analiz sayfası (tekli ve toplu).
    - `login.html` / `register.html`: Kullanıcı giriş ve kayıt sayfaları.
    - `assignments.html`: Atama yönetimi paneli.
    - `toplu_tasima.html`: Toplu taşıma rotalarını gösteren sayfa.
- `static/`: Logo ve arka plan resimleri gibi statik dosyaları içerir.
- `requirements.txt`: Projenin çalışması için gerekli olan Python kütüphanelerini listeler.
- `*.xlsx`: Kullanıcı, atama gibi verilerin saklandığı Excel dosyaları.
- `*.json`: API'den alınan adres verilerini önbelleğe almak için kullanılan dosyalar.
