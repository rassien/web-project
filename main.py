import pandas as pd
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import time

# Kullanıcıdan dosya adı ve sayfa adlarını al
excel_yolu = input("Excel dosyasının yolunu girin: ")
calisan_sayfa = input("Çalışanlar sayfa adını girin: ")
sube_sayfa = input("Şubeler sayfa adını girin: ")

# Excel'den verileri oku
calisanlar_df = pd.read_excel(excel_yolu, sheet_name=calisan_sayfa)
subeler_df = pd.read_excel(excel_yolu, sheet_name=sube_sayfa)

# Sütun adlarını küçük harfe çevir
calisanlar_df.columns = [c.lower() for c in calisanlar_df.columns]
subeler_df.columns = [c.lower() for c in subeler_df.columns]

# Çalışan ve şube adresi sütunlarını otomatik bul
calisan_ad_kolon = [c for c in calisanlar_df.columns if "ad" in c][0]
calisan_adres_kolon = [c for c in calisanlar_df.columns if "adres" in c][0]
sube_ad_kolon = [c for c in subeler_df.columns if "şube" in c or "sube" in c][0]
sube_adres_kolon = [c for c in subeler_df.columns if "adres" in c][0]

# Geocoder başlat
geolocator = Nominatim(user_agent="adres_karsilastirma_app")

def adresi_konuma_cevir(adres):
    konum = None
    try:
        konum = geolocator.geocode(adres)
        if not konum:
            konum = geolocator.geocode(adres + ", Türkiye")
    except Exception:
        pass
    time.sleep(1)  # Rate limit
    return konum

# Şubelerin koordinatlarını bul
print("Şube adresleri geocode ediliyor...")
sube_konumlari = []
for i, row in subeler_df.iterrows():
    ad = row[sube_ad_kolon]
    adres = row[sube_adres_kolon]
    konum = adresi_konuma_cevir(str(adres))
    sube_konumlari.append({
        'ad': ad,
        'adres': adres,
        'lat': konum.latitude if konum else None,
        'lon': konum.longitude if konum else None
    })
print("Şube adresleri tamamlandı.")

# Sonuçları tutacak liste
sonuclar = []
print("Çalışan adresleri işleniyor ve en yakın şube bulunuyor...")
for i, row in calisanlar_df.iterrows():
    calisan_ad = row[calisan_ad_kolon]
    calisan_adres = row[calisan_adres_kolon]
    calisan_konum = adresi_konuma_cevir(str(calisan_adres))
    if not calisan_konum:
        print(f"{calisan_ad} için adres bulunamadı!")
        continue
    min_mesafe = float('inf')
    en_yakin_sube = None
    for sube in sube_konumlari:
        if sube['lat'] is not None and sube['lon'] is not None:
            mesafe = geodesic(
                (calisan_konum.latitude, calisan_konum.longitude),
                (sube['lat'], sube['lon'])
            ).kilometers
            if mesafe < min_mesafe:
                min_mesafe = mesafe
                en_yakin_sube = sube
    if en_yakin_sube:
        sonuclar.append({
            'Çalışan Adı': calisan_ad,
            'Çalışan Adresi': calisan_adres,
            'En Yakın Şube': en_yakin_sube['ad'],
            'Şube Adresi': en_yakin_sube['adres'],
            'Mesafe (km)': round(min_mesafe, 2)
        })
    else:
        sonuclar.append({
            'Çalışan Adı': calisan_ad,
            'Çalışan Adresi': calisan_adres,
            'En Yakın Şube': None,
            'Şube Adresi': None,
            'Mesafe (km)': None
        })

# Sonuçları DataFrame olarak göster
sonuc_df = pd.DataFrame(sonuclar)
print("\nSonuçlar:")
print(sonuc_df)
# İsterseniz Excel'e de kaydedebilirsiniz:
sonuc_df.to_excel("calisan_en_yakin_sube_sonuclar.xlsx", index=False)
print("\nSonuçlar 'calisan_en_yakin_sube_sonuclar.xlsx' dosyasına kaydedildi.") 