Proje Süreçleri Hakkında Açıklama
1. Kullanıcı Kayıt ve Giriş Süreci
•	Amaç: Sisteme sadece yetkili kullanıcıların erişmesini sağlamak.
•	İşleyiş:
•	Kullanıcılar, kayıt ekranından kullanıcı adı ve şifre ile kayıt olabilir.
•	Giriş ekranında doğrulama yapılır, başarılı giriş sonrası ana sayfaya yönlendirilir.
•	Flask-Login ile oturum yönetimi sağlanır.
________________________________________
2. Çalışan ve Şube Verilerinin Yüklenmesi
•	Amaç: Atama işlemleri için gerekli olan çalışan ve şube verilerinin sisteme alınması.
•	İşleyiş:
•	Kullanıcı, analiz ekranında Excel dosyası yükler.
•	Dosyadan çalışanların adı ve adresi ile şubelerin adı, adresi ve norm kadro (kapasite) bilgileri okunur.
•	Veriler frontend’de ve backend’de uygun veri yapısına dönüştürülür.
________________________________________
3. En Yakın Şubelerin Hesaplanması (Analiz)
•	Amaç: Her çalışan için en yakın n şubeyi bulmak.
•	İşleyiş:
•	Her çalışanın adresi ile tüm şubelerin adresleri arasındaki mesafeler hesaplanır (Google Maps API ve haversine formülü kullanılır).
•	Her çalışan için mesafeye göre en yakın n şube sıralanır.
•	Bu bilgiler, toplu atama için kullanılır.
________________________________________
4. Toplu Atama ve Norm Kadro Güncelleme
•	Amaç: Her çalışanın en uygun şubeye atanmasını ve şube kapasitesinin güncellenmesini sağlamak.
•	İşleyiş:
•	Kullanıcı “Kaydet” butonuna bastığında, sistem her çalışan için en yakın n şubeyi kontrol eder.
•	Şubenin norm_kadro değeri > 0 ise atama yapılır, norm_kadro 1 azaltılır.
•	Eğer n şube içinde uygun şube yoksa, çalışan “atanamadı” olarak işaretlenir.
•	Aynı çalışana birden fazla atama yapılmak istenirse sistem işlemi durdurur ve kullanıcıya uyarı verir.
•	Yapılan atamalar ve güncel normlar assignments.xlsx dosyasına kaydedilir.
________________________________________
5. Atama Sonuçlarının ve Normların Görüntülenmesi
•	Amaç: Kullanıcıya yapılan atamaları ve güncel şube normlarını anlık olarak göstermek.
•	İşleyiş:
•	Atama sonuçları frontend’de tablo olarak gösterilir.
•	Her çalışanın hangi şubeye atandığı, atama durumu ve şubenin güncel norm kadro değeri ekranda görünür.
________________________________________
6. Excel’e Aktarma
•	Amaç: Kullanıcının atama sonuçlarını ve güncel normları dışa aktarabilmesini sağlamak.
•	İşleyiş:
•	Kullanıcı “Excel’e Aktar” butonuna tıkladığında, sistem assignments.xlsx dosyasını hazırlar ve indirir.
•	Dosyada tüm atama kayıtları ve şubelerin güncel norm kadro değerleri bulunur.
________________________________________
7. Hata ve Uyarı Yönetimi
•	Amaç: Kullanıcı hatalı işlem yaptığında bilgilendirmek ve veri bütünlüğünü korumak.
•	İşleyiş:
•	Aynı çalışana birden fazla atama yapılmak istenirse, sistem işlemi durdurur ve Türkçe uyarı mesajı gösterir.
•	Eksik veri veya beklenmeyen hata durumlarında kullanıcıya açıklayıcı hata mesajı sunulur.
________________________________________
8. Kod Kalitesi ve Geliştirilebilirlik
•	Amaç: Kodun sürdürülebilir, okunabilir ve kolayca geliştirilebilir olmasını sağlamak.
•	İşleyiş:
•	Anlamlı değişken ve fonksiyon isimleri kullanılır.
•	Fonksiyonlar kısa ve tek sorumluluk ilkesine uygun yazılır.
•	Gereksiz yorumlardan kaçınılır, kodun kendisi açıklayıcı olacak şekilde tasarlanır.
•	Yeni kurallar veya ek kontroller kolayca entegre edilebilir.
________________________________________
Sonuç
Bu proje, çalışanların en uygun şubelere adil ve otomatik şekilde atanmasını, şube kapasitesinin (norm kadro) dinamik olarak yönetilmesini ve tüm sürecin kullanıcı dostu bir arayüzle kolayca yönetilmesini sağlar. Tüm süreçler, veri bütünlüğü ve kullanıcı deneyimi ön planda tutularak tasarlanmıştır.
