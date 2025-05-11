from flask import Flask, render_template, request, jsonify, send_file
from geopy.geocoders import GoogleV3
import folium
from folium.plugins import MarkerCluster
import pandas as pd
import os
from dotenv import load_dotenv
import math
import requests
from datetime import datetime
import io

# .env dosyasından API anahtarını yükle
load_dotenv()
GOOGLE_MAPS_API_KEY = os.getenv('GOOGLE_MAPS_API_KEY')

app = Flask(__name__)

# GoogleV3 geocoder'ı başlat
geolocator = GoogleV3(api_key=GOOGLE_MAPS_API_KEY)

def get_distance_and_duration(origin, destination):
    url = f"https://maps.googleapis.com/maps/api/distancematrix/json?origins={origin}&destinations={destination}&key={GOOGLE_MAPS_API_KEY}"
    response = requests.get(url)
    data = response.json()
    
    if data['status'] == 'OK':
        element = data['rows'][0]['elements'][0]
        if element['status'] == 'OK':
            return {
                'distance': element['distance']['value'] / 1000,  # km cinsinden
                'duration': element['duration']['value'] / 60  # dakika cinsinden
            }
    return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/export-excel', methods=['POST'])
def export_excel():
    try:
        data = request.get_json()
        results = data.get('results', [])
        employee_names = data.get('employee_names', [])  # Yeni: çalışan adları
        
        if not results:
            return jsonify({'error': 'Veri bulunamadı'}), 400

        # Sadece en yakın şube ve hatasız satırlar
        excel_data = []
        for idx, result in enumerate(results):
            if result['status'] == 'success' and result.get('nearest_branches'):
                branch = result['nearest_branches'][0]
                employee_name = employee_names[idx] if idx < len(employee_names) else ''
                excel_data.append({
                    'Çalışan Adı': employee_name,
                    'Çalışan Adresi': result['address'],
                    'Şube Adı': branch.get('sube_adi', ''),
                    'Şube Adresi': branch.get('sube_adres', ''),
                    'Mesafe (km)': round(branch.get('mesafe', 0), 2),
                    'Tahmini Süre (dk)': round(branch.get('sure', 0))
                })

        if not excel_data:
            return jsonify({'error': 'Aktarılacak uygun veri yok'}), 400

        df = pd.DataFrame(excel_data)
        output = io.BytesIO()
        df.to_excel(output, index=False, sheet_name='En Yakın Şube')
        output.seek(0)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'en_yakin_sube_{timestamp}.xlsx'
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

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
                            distance_info = get_distance_and_duration(
                                f"{location.latitude},{location.longitude}",
                                f"{sube['lat']},{sube['lon']}"
                            )
                            if distance_info:
                                mesafeler.append({
                                    'sube_adi': sube['ad'],
                                    'sube_adres': sube['adres'],
                                    'mesafe': distance_info['distance'],
                                    'sure': distance_info['duration'],
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
                        popup=f"Adres: {result['address']}",
                        icon=folium.Icon(color='blue', icon='info-sign')
                    ).add_to(marker_cluster)
                    # En yakın şubeleri de ekle
                    for sube in result.get('nearest_branches', []):
                        folium.Marker(
                            [sube['lat'], sube['lon']],
                            popup=f"Şube: {sube['sube_adi']}<br>Adres: {sube['sube_adres']}<br>Mesafe: {sube['mesafe']:.2f} km<br>Tahmini Süre: {sube['sure']:.0f} dakika",
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