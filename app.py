from flask import Flask, render_template, request, jsonify
from geopy.geocoders import GoogleV3
import folium
from folium.plugins import MarkerCluster
import pandas as pd
import os
from dotenv import load_dotenv
import math

# .env dosyasından API anahtarını yükle
load_dotenv()
GOOGLE_MAPS_API_KEY = os.getenv('GOOGLE_MAPS_API_KEY')

app = Flask(__name__)

# GoogleV3 geocoder'ı başlat
geolocator = GoogleV3(api_key=GOOGLE_MAPS_API_KEY)

def haversine(lon1, lat1, lon2, lat2):
    # Dünya yarıçapı (km)
    R = 6371.0
    lon1, lat1, lon2, lat2 = map(math.radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    return R * c

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/geocode', methods=['POST'])
def geocode():
    try:
        data = request.get_json()
        addresses = data.get('addresses', [])
        k = int(data.get('k', 3))
        
        if not addresses:
            return jsonify({'error': 'Adres listesi boş'}), 400

        # Şube adreslerini oku
        sube_df = pd.read_excel('subeler.xlsx')
        sube_adresler = sube_df['Adres'].tolist()
        sube_adlari = sube_df['Şube Adı'].tolist()

        # Şubelerin koordinatlarını bul
        sube_coords = []
        for ad, adres in zip(sube_adlari, sube_adresler):
            try:
                loc = geolocator.geocode(adres)
                if loc:
                    sube_coords.append({'ad': ad, 'adres': adres, 'lat': loc.latitude, 'lon': loc.longitude})
                else:
                    sube_coords.append({'ad': ad, 'adres': adres, 'lat': None, 'lon': None})
            except Exception as e:
                sube_coords.append({'ad': ad, 'adres': adres, 'lat': None, 'lon': None, 'error': str(e)})

        # Sonuçları saklamak için liste
        results = []
        for address in addresses:
            try:
                location = geolocator.geocode(address)
                if location:
                    # Mesafeleri hesapla
                    mesafeler = []
                    for sube in sube_coords:
                        if sube['lat'] is not None and sube['lon'] is not None:
                            mesafe = haversine(location.longitude, location.latitude, sube['lon'], sube['lat'])
                            mesafeler.append({
                                'sube_adi': sube['ad'],
                                'sube_adres': sube['adres'],
                                'mesafe': mesafe,
                                'lat': sube['lat'],
                                'lon': sube['lon']
                            })
                    # En yakın k şubeyi bul
                    mesafeler = sorted(mesafeler, key=lambda x: x['mesafe'])[:k]
                    results.append({
                        'address': address,
                        'latitude': location.latitude,
                        'longitude': location.longitude,
                        'status': 'success',
                        'nearest_branches': mesafeler
                    })
                else:
                    results.append({
                        'address': address,
                        'status': 'error',
                        'message': 'Adres bulunamadı'
                    })
            except Exception as e:
                results.append({
                    'address': address,
                    'status': 'error',
                    'message': str(e)
                })

        # Harita oluştur
        if any(r['status'] == 'success' for r in results):
            m = folium.Map(location=[41.0082, 28.9784], zoom_start=10)
            marker_cluster = MarkerCluster().add_to(m)
            for result in results:
                if result['status'] == 'success':
                    folium.Marker(
                        [result['latitude'], result['longitude']],
                        popup=f"Adres: {result['address']}"
                    ).add_to(marker_cluster)
                    # En yakın şubeleri de ekle
                    for sube in result.get('nearest_branches', []):
                        folium.Marker(
                            [sube['lat'], sube['lon']],
                            popup=f"Şube: {sube['sube_adi']}<br>Adres: {sube['sube_adres']}<br>Mesafe: {sube['mesafe']:.2f} km",
                            icon=folium.Icon(color='red', icon='info-sign')
                        ).add_to(marker_cluster)
            map_html = m._repr_html_()
        else:
            map_html = None

        return jsonify({
            'results': results,
            'map_html': map_html
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True) 