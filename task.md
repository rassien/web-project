Aşağıya, Cursor’da (“prompts” bölümüne yapıştırabileceğin) tek seferde çalışacak, ayrıntılı bir talimat (prompt) hazırladım. İhtiyacın olan “toplu analiz → kaydet” akışını ve norm güncelleme kurallarını içeriyor:

```
/*
Bulk Atama & Norm Güncelleme Modülü
-----------------------------------

Senaryo:
  - Kullanıcı, toplu analiz ekranında bir Excel dosyası yükleyip “n” adet en yakın şubeyi seçecek.
  - “Kaydet” butonuna bastığında, her çalışan için en yakın 1. şubeden başlayarak otomatik atama yapılacak.
  - Atamalar, atama yönetimi sayfası (assignments_page) üzerinde anında görünecek.
  - Her atama sonrası ilgili şubenin `norm_kadro` değeri 1 azalacak.
  - Eğer bir şubenin `norm_kadro` değeri 0’dan küçük ya da kullanıcı tarafından belirlenen “n” limiti içinde zaten doluysa, bu şubeye atama yapılmayacak; bir sonraki en yakın şubeye geçilecek.
  - Bu seçim döngüsü, her çalışan için en fazla “n” şube kontrol edilene kadar devam edecek.
  - Atama tamamlandığında tüm güncellenmiş `norm_kadro` değerleri ve yapılan atama kayıtları Excel’e (.xlsx) aktarılabilecek.

Adım Adım Uygulama:

1. Excel’den gelen çalışan listesi ve şube verilerini oku.  
2. Kullanıcının analiz ekranında seçtiği “n” parametresini al.  
3. Her bir çalışan için:  
   a. Şubeleri, çalışan–şube mesafesine göre artan sırada sırala.  
   b. Sıradaki her şube için:  
      i. Eğer `norm_kadro > 0` ise:  
         - Şubeye atanacak çalışanın kaydını oluştur.  
         - Şubenin `norm_kadro -= 1`.  
         - Atamayı assignments_page’e ekle.  
         - Bu çalışanın atama sürecini sonlandır (bir rest atama).  
      ii. Değilse (`norm_kadro <= 0`), bir sonraki en yakın şubeye geç.  
      iii. Toplamda “n” şube kontrolü bittiğinde hala atama yapılmadıysa, çalışan için “atanamadı” durumu göster.  
4. Tüm çalışanlar için döngü bittiğinde:  
   - assignments_page üzerindeki tablo güncellensin.  
   - Kullanıcı isterse “Excel’e aktar” butonuyla yeni atama kayıtlarını ve güncel norm değerlerini indirilebilecek bir .xlsx dosyası olarak dışa aktarabilsin.  
5. Yeni atama mantığını, `assignments.html` ve backend’deki `save_bulk_assignments()` fonksiyonuna entegre et.

Bu akışı, Cursor’a yapıştır ve gerekli yerlere uygun fonksiyon/ad alanı isimlerini adapte et. Başarılar!
```
