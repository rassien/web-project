# Uygulama Kurulum ve Dağıtım Hazırlıkları

Bu doküman, "Çalışan Şube Eşleştirme ve Atama Sistemi" uygulamasının teknik gereksinimlerini, kurulum adımlarını ve temel kullanımını özetlemektedir.

## 1. Uygulamanın Gereksinimleri

### a. Port Bilgisi
Uygulama, standart bir Flask geliştirme sunucusunda çalışır ve varsayılan olarak **5000** numaralı portu kullanır. Bu port, `main.py` dosyası içerisinden veya uygulamayı çalıştırırken bir parametre ile değiştirilebilir.

### b. Kullanılan Teknolojiler
Proje, aşağıdaki teknolojiler ve kütüphaneler üzerine kurulmuştur:
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

*Not: Projede Nginx gibi bir "reverse proxy" veya WSGI sunucusu (Gunicorn, uWSGI) production ortamı için ayrıca yapılandırılabilir, ancak mevcut haliyle geliştirme sunucusuyla çalışmaktadır.*

### c. Uygulama Dosyalarının Konumu
Uygulamanın tüm kaynak kodları ve ilgili dosyaları `C:\Users\90530\OneDrive\Masaüstü\web-project` klasöründe yer almaktadır.

### d. Erişim Bilgisi
Uygulama, bir kullanıcı kayıt ve giriş sistemine sahiptir. `proje_aciklamasi.md` dosyasında belirtildiği gibi, bu sistem çalışan atamalarını yönetmek için tasarlanmıştır. Dolayısıyla, uygulamanın sadece ilgili birim çalışanları (örneğin, İnsan Kaynakları veya şube yöneticileri) tarafından kullanılması hedeflenmektedir. Erişim halka açık değildir.

## 2. Test ve Belgeler

### a. Kurulum ve Çalıştırma Adımları

1.  **Python Kurulumu:** Makinenizde Python 3.x sürümünün kurulu olduğundan emin olun.
2.  **Proje Dosyalarını Hazırlama:** Proje dosyalarının bulunduğu ana dizine gidin.
3.  **Sanal Ortam (Virtual Environment) Oluşturma:**
    ```bash
    python -m venv .venv
    ```
4.  **Sanal Ortamı Aktifleştirme:**
    - **Windows:**
      ```bash
      .\.venv\Scripts\activate
      ```
    - **macOS/Linux:**
      ```bash
      source .venv/bin/activate
      ```
5.  **Gerekli Kütüphaneleri Yükleme:**
    ```bash
    pip install -r requirements.txt
    ```
6.  **Ortam Değişkenlerini Ayarlama:**
    - Proje ana dizininde bulunan `.env.example` dosyasını kopyalayarak `.env` adında yeni bir dosya oluşturun.
    - `.env` dosyasını açın ve `GOOGLE_MAPS_API_KEY` değişkenine kendi Google Haritalar API anahtarınızı girin.
7.  **Uygulamayı Çalıştırma:**
    ```bash
    flask run
    ```
    Uygulama başlatıldığında, terminalde `Running on http://127.0.0.1:5000` gibi bir çıktı göreceksiniz.

### b. Kısa Kullanım Kılavuzu

1.  **Giriş:** Web tarayıcınızdan `http://127.0.0.1:5000` adresine gidin.
2.  **Kayıt/Giriş:** İlk defa kullanıyorsanız "Kayıt Ol" ekranından bir kullanıcı oluşturun. Zaten bir hesabınız varsa "Giriş Yap" ekranını kullanın.
3.  **Ana Analiz Sayfası (`index.html`):**
    - **Tek Adres Analizi:** Bir çalışanın adresini girerek en yakın şubeleri listeleyin.
    - **Toplu Analiz:** Sistemde kayıtlı çalışan ve şube verilerini içeren bir Excel dosyası yükleyerek toplu eşleştirme yapın.
4.  **Atama Yönetimi (`assignments.html`):**
    - Yapılan analizler sonucunda çalışanları şubelere atayın.
    - Mevcut atamaları görüntüleyin, düzenleyin, silin veya Excel olarak dışa aktarın.
5.  **Toplu Taşıma (`toplu_tasima.html`):**
    - Belirli bir çalışan ve şube arasındaki toplu taşıma seçeneklerini ve rota detaylarını görüntüleyin.
