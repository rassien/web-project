from flask import Flask, render_template, request, jsonify, make_response, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import pandas as pd
from geopy.geocoders import GoogleV3
import os
from dotenv import load_dotenv
import requests
import json
from io import BytesIO
import math
from concurrent.futures import ThreadPoolExecutor, as_completed
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Flask-Login yapılandırması
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, id, username, password_hash):
        self.id = id
        self.username = username
        self.password_hash = password_hash

USERS_FILE = "users.xlsx"

def load_users():
    if os.path.exists(USERS_FILE):
        df = pd.read_excel(USERS_FILE)
        users = {}
        for _, row in df.iterrows():
            users[row['username']] = User(
                id=row['id'],
                username=row['username'],
                password_hash=row['password_hash']
            )
        return users
    return {}

def save_users(users):
    data = []
    for username, user in users.items():
        data.append({
            'id': user.id,
            'username': user.username,
            'password_hash': user.password_hash
        })
    df = pd.DataFrame(data)
    df.to_excel(USERS_FILE, index=False)

users = load_users()

@login_manager.user_loader
def load_user(user_id):
    for user in users.values():
        if str(user.id) == str(user_id):
            return user
    return None

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username in users:
            flash('Bu kullanıcı adı zaten kullanılıyor!')
            return redirect(url_for('register'))
        user_id = len(users) + 1
        password_hash = generate_password_hash(password)
        users[username] = User(user_id, username, password_hash)
        save_users(users)
        flash('Kayıt başarılı! Şimdi giriş yapabilirsiniz.')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = users.get(username)
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('index'))
        flash('Geçersiz kullanıcı adı veya şifre!')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# .env dosyasından API anahtarını yükle
load_dotenv()
GOOGLE_MAPS_API_KEY = os.getenv('GOOGLE_MAPS_API_KEY')
geolocator = GoogleV3(api_key=GOOGLE_MAPS_API_KEY)

CACHE_FILE = "adres_cache.json"
if os.path.exists(CACHE_FILE):
    with open(CACHE_FILE, "r", encoding="utf-8") as f:
        adres_cache = json.load(f)
else:
    adres_cache = {}

def save_cache():
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(adres_cache, f, ensure_ascii=False, indent=2)

def get_coordinates_cached(address: str) -> tuple:
    address = address.strip()
    if address in adres_cache:
        return tuple(adres_cache[address])
    try:
        location = geolocator.geocode(address)
        if location:
            adres_cache[address] = [location.latitude, location.longitude]
            save_cache()
            return (location.latitude, location.longitude)
    except Exception:
        return None
    return None

def get_distance_and_duration_batch(origin, destinations):
    dest_str = "|".join([f"{lat},{lon}" for lat, lon in destinations])
    url = f"https://maps.googleapis.com/maps/api/distancematrix/json?origins={origin}&destinations={dest_str}&key={GOOGLE_MAPS_API_KEY}"
    response = requests.get(url)
    data = response.json()
    results = []
    if data['status'] == 'OK':
        elements = data['rows'][0]['elements']
        for el in elements:
            if el['status'] == 'OK':
                results.append({
                    'distance': el['distance']['value'] / 1000,
                    'duration': el['duration']['value'] / 60
                })
            else:
                results.append(None)
    return results

def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def process_single_address_batch(calisan_adi, calisan_adresi, sube_coords, k, max_distance_km=None, filter_by_city=False, haversine_limit=10):
    result = {
        'calisan_adi': calisan_adi,
        'address': calisan_adresi,
        'status': 'fail',
        'nearest_branches': []
    }
    location = get_coordinates_cached(calisan_adresi)
    if not location:
        return result
    result['latitude'] = location[0]
    result['longitude'] = location[1]
    origin = f"{location[0]},{location[1]}"
    for sube in sube_coords:
        sube['hava_mesafe'] = haversine(location[0], location[1], sube['lat'], sube['lon'])
    yakinlar = sorted(sube_coords, key=lambda x: x['hava_mesafe'])[:haversine_limit]
    destinations = [(sube['lat'], sube['lon']) for sube in yakinlar]
    mesafe_sure_list = get_distance_and_duration_batch(origin, destinations)
    mesafeler = []
    for sube, distance_info in zip(yakinlar, mesafe_sure_list):
        if distance_info:
            distance_km = distance_info['distance']
            if max_distance_km and distance_km > max_distance_km:
                continue
            sube_data = {
                'sube_adi': sube['ad'],
                'sube_adres': sube['adres'],
                'mesafe': distance_km,
                'sure': distance_info['duration'],
                'lat': sube['lat'],
                'lon': sube['lon'],
                'norm': sube.get('norm', 0)
            }
            mesafeler.append(sube_data)
    mesafeler = sorted(mesafeler, key=lambda x: x['mesafe'])[:k]
    mesafeler = sorted(mesafeler, key=lambda x: x['norm'])
    if mesafeler:
        result['status'] = 'success'
        result['nearest_branches'] = mesafeler
    return result

@app.route('/')
@login_required
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
@login_required
def analyze():
    try:
        data = request.json
        calisan_adi = data.get('calisan_adi')
        calisan_adresi = data.get('calisan_adresi')
        subeler = data.get('subeler', [])
        ad_column = data.get('ad_column', 'ad')
        adres_column = data.get('adres_column', 'adres')
        k = int(data.get('k', 3))
        max_distance_km = float(data.get('max_distance_km', 30))
        filter_by_city = data.get('filter_by_city', False)
        sube_coords = []
        for sube in subeler:
            ad = sube.get(ad_column)
            adres = sube.get(adres_column)
            coords = get_coordinates_cached(adres)
            if coords:
                sube_dict = {
                    'ad': ad,
                    'adres': adres,
                    'lat': coords[0],
                    'lon': coords[1],
                    'norm': sube.get('norm', 0)
                }
                sube_coords.append(sube_dict)
        result = process_single_address_batch(
            calisan_adi,
            calisan_adresi,
            sube_coords,
            k,
            max_distance_km if max_distance_km > 0 else None,
            filter_by_city
        )
        return jsonify(result)
    except Exception as e:
        import traceback
        print("Hata:", e)
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/download_results', methods=['POST'])
@login_required
def download_results():
    try:
        data = request.json
        results = data.get('results', [])
        excel_data = []
        for branch in results:
            excel_data.append({
                'Çalışan Adı': branch.get('calisan_adi', ''),
                'Çalışan Adresi': branch.get('address', ''),
                'Şube Adı': branch.get('sube_adi', ''),
                'Şube Adresi': branch.get('sube_adres', ''),
                'Mesafe (km)': round(branch.get('mesafe', 0), 2),
                'Araçla Süre (dk)': round(branch.get('sure', 0)),
                'Norm': branch.get('norm', '')
            })
        df = pd.DataFrame(excel_data)
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Sonuçlar')
            worksheet = writer.sheets['Sonuçlar']
            worksheet.set_column(0, len(df.columns)-1, 20)
        output.seek(0)
        response = make_response(output.read())
        response.headers["Content-Disposition"] = "attachment; filename=sonuclar.xlsx"
        response.headers["Content-type"] = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        return response
    except Exception as e:
        import traceback
        print("Excel indirme hatası:", e)
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/bulk_analyze', methods=['POST'])
@login_required
def bulk_analyze():
    try:
        data = request.json
        calisanlar = data.get('calisanlar', [])
        subeler = data.get('subeler', [])
        calisan_ad_column = data.get('calisan_ad_column', 'ad')
        calisan_adres_column = data.get('calisan_adres_column', 'adres')
        sube_ad_column = data.get('sube_ad_column', 'ad')
        sube_adres_column = data.get('sube_adres_column', 'adres')
        k = int(data.get('k', 3))
        max_distance_km = float(data.get('max_distance_km', 30))
        filter_by_city = data.get('filter_by_city', False)
        sube_coords = []
        for sube in subeler:
            ad = sube.get(sube_ad_column)
            adres = sube.get(sube_adres_column)
            coords = get_coordinates_cached(adres)
            if coords:
                sube_dict = {
                    'ad': ad,
                    'adres': adres,
                    'lat': coords[0],
                    'lon': coords[1],
                    'norm': sube.get('norm', 0)
                }
                sube_coords.append(sube_dict)
        results = []
        with ThreadPoolExecutor(max_workers=8) as executor:
            future_to_row = {
                executor.submit(
                    process_single_address_batch,
                    row.get(calisan_ad_column),
                    row.get(calisan_adres_column),
                    sube_coords,
                    k,
                    max_distance_km if max_distance_km > 0 else None,
                    filter_by_city
                ): row for row in calisanlar
            }
            for future in as_completed(future_to_row):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as exc:
                    results.append({'status': 'fail', 'error': str(exc)})
        return jsonify(results)
    except Exception as e:
        import traceback
        print("Toplu analiz hatası:", e)
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True) 