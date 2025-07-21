from flask import Flask, render_template, request, jsonify, make_response, redirect, url_for, send_file
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import pandas as pd
from geopy.geocoders import GoogleV3
import os
from dotenv import load_dotenv
import json
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor, as_completed
from werkzeug.security import generate_password_hash, check_password_hash
import datetime
import re
import math
import requests
import traceback

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
    """
    Kullanıcıları USERS_FILE'dan yükler ve User nesneleri olarak döndürür.
    """
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
    """
    Kullanıcıları USERS_FILE'a kaydeder.
    """
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

def add_user(users, username, password):
    """Yeni kullanıcıyı ekler ve şifreyi hash'ler."""
    user_id = len(users) + 1
    password_hash = generate_password_hash(password)
    users[username] = User(user_id, username, password_hash)
    save_users(users)
    return users[username]

def validate_user(users, username, password):
    """Kullanıcı adı ve şifreyi doğrular."""
    user = users.get(username)
    if user and check_password_hash(user.password_hash, password):
        return user
    return None

# register ve login fonksiyonlarında bu yardımcı fonksiyonları kullanacak şekilde kodu sadeleştiriyorum.

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username in users:
            return redirect(url_for('register'))
        add_user(users, username, password)
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = validate_user(users, username, password)
        if user:
            login_user(user)
            return redirect(url_for('index'))
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
    """
    Adresin koordinatlarını cache'den veya Google Maps API'dan döndürür.
    """
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

def process_single_address_batch(calisan_adi, calisan_adresi, sube_coords, k, max_distance_km=None, filter_by_city=False, haversine_limit=10, tckn=''):
    """
    Bir çalışanın adresi için en yakın şubeleri ve mesafeleri hesaplar.
    """
    result = {
        'calisan_adi': calisan_adi,
        'address': calisan_adresi,
        'status': 'fail',
        'nearest_branches': [],
        'tckn': tckn
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
    mesafeler = sorted(mesafeler, key=lambda x: x['mesafe'])
    
    # Normu 2'den küçük olanları filtrele
    mesafeler = [m for m in mesafeler if m.get('norm', 0) < 2]

    # Son olarak k adet şubeyi al
    mesafeler = mesafeler[:k]
    
    mesafeler = sorted(mesafeler, key=lambda x: x['norm'])
    if mesafeler:
        result['status'] = 'success'
        result['nearest_branches'] = mesafeler
    return result

@app.route('/')
@login_required
def index():
    return render_template('index.html', google_maps_api_key=GOOGLE_MAPS_API_KEY)

@app.route('/analyze', methods=['POST'])
@login_required
def analyze():
    try:
        data = request.json
        calisan_adi = data.get('calisan_adi')
        tckn = data.get('tckn', '')
        if not tckn or str(tckn).strip() == '':
            return jsonify({'error': 'TCKN zorunlu bir alandır.'}), 400
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
            filter_by_city,
            tckn=tckn
        )
        return jsonify(result)
    except Exception as e:
        print("Hata:", e)
        return jsonify({'error': str(e)}), 500

@app.route('/download_results', methods=['POST'])
@login_required
def download_results():
    try:
        data = request.json
        results = data.get('results', [])
        excel_data = []
        for branch in results:
            toplu_tasima_url = f"http://127.0.0.1:5000/toplu_tasima?calisan_adresi={branch.get('address','')}&sube_adresleri={branch.get('sube_adres','')}"
            excel_data.append({
                'TCKN': branch.get('tckn', ''),
                'Çalışan Adı': branch.get('calisan_adi', ''),
                'Çalışan Adresi': branch.get('address', ''),
                'Şube Adı': branch.get('sube_adi', ''),
                'Şube Adresi': branch.get('sube_adres', ''),
                'Mesafe (km)': round(branch.get('mesafe', 0) or 0, 2) if branch.get('mesafe') not in [None, ''] else '',
                'Araçla Süre (dk)': round(branch.get('sure', 0) or 0) if branch.get('sure') not in [None, ''] else '',
                'Norm': branch.get('norm', ''),
                'Toplu Taşıma Linki': toplu_tasima_url
            })
        df = pd.DataFrame(excel_data)
        # Sütun sırasını ayarla: TCKN, Çalışan Adı, ...
        columns = ['TCKN', 'Çalışan Adı', 'Çalışan Adresi', 'Şube Adı', 'Şube Adresi', 'Mesafe (km)', 'Araçla Süre (dk)', 'Norm', 'Toplu Taşıma Linki']
        df = df[columns]
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
        print("Excel indirme hatası:", e)
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
                    filter_by_city,
                    tckn=row.get('tckn')
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
        print("Toplu analiz hatası:", e)
        return jsonify({'error': str(e)}), 500

ASSIGNMENTS_FILE = "assignments.xlsx"

# Atama dosyasını yükle veya oluştur
def load_assignments():
    if os.path.exists(ASSIGNMENTS_FILE):
        return pd.read_excel(ASSIGNMENTS_FILE)
    else:
        df = pd.DataFrame(columns=[
            'TCKN', 'Çalışan Adı', 'Çalışan Adresi', 'Şube Adı', 'Şube Adresi', 'Mesafe (km)', 'Süre (dk)', 'Atama Tarihi', 'Norm'
        ])
        df.to_excel(ASSIGNMENTS_FILE, index=False)
        return df

def save_assignments(df):
    df.to_excel(ASSIGNMENTS_FILE, index=False)

def update_branch_value(sube_ad, sube_adres, delta, subeler, key='norm', ad_col='ad', adres_col='adres'):
    """
    Şube norm veya norm_kadro değerini günceller.
    """
    for sube in subeler:
        if sube.get(ad_col) == sube_ad and sube.get(adres_col) == sube_adres:
            sube[key] = sube.get(key, 0) + delta
    return subeler

# Toplu atama ve norm güncelleme (task.md senaryosu)
def save_bulk_assignments(assignments, subeler, n, sube_ad_column='ad', sube_adres_column='adres'):
    df = load_assignments()
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
    atama_kayitlari = []
    for atama in assignments:
        calisan_adi = atama['calisan_adi']
        calisan_adresi = atama['calisan_adresi']
        yakin_subeler = atama['yakin_subeler']  # [{'sube_adi':..., 'sube_adres':..., 'mesafe':..., ...}, ...]
        atandi = False
        for sube in yakin_subeler[:n]:
            sube_adi = sube['sube_adi']
            sube_adres = sube['sube_adres']
            # Şubenin norm_kadro değerini bul
            norm_kadro = None
            for s in subeler:
                if s.get(sube_ad_column) == sube_adi and s.get(sube_adres_column) == sube_adres:
                    norm_kadro = s.get('norm_kadro', s.get('norm', 0))
            if norm_kadro is None:
                continue
            if norm_kadro > 0:
                # Atama kaydını oluştur
                new_row = pd.DataFrame([{
                    'TCKN': '', # TCKN bilgisi burada eklenecek
                    'Çalışan Adı': calisan_adi,
                    'Çalışan Adresi': calisan_adresi,
                    'Şube Adı': sube_adi,
                    'Şube Adresi': sube_adres,
                    'Atama Tarihi': now,
                    'Norm': norm_kadro - 1
                }])
                df = pd.concat([df, new_row], ignore_index=True)
                # Normu azalt
                subeler = update_branch_value(sube_adi, sube_adres, -1, subeler, key='norm_kadro', ad_col=sube_ad_column, adres_col=sube_adres_column)
                atama_kayitlari.append({
                    'calisan_adi': calisan_adi,
                    'calisan_adresi': calisan_adresi,
                    'sube_adi': sube_adi,
                    'sube_adres': sube_adres,
                    'atama_durumu': 'atandı',
                    'norm_kadro': norm_kadro - 1
                })
                atandi = True
                break  # Bir çalışana sadece bir atama yapılır
        if not atandi:
            atama_kayitlari.append({
                'calisan_adi': calisan_adi,
                'calisan_adresi': calisan_adresi,
                'sube_adi': '',
                'sube_adres': '',
                'atama_durumu': 'atanamadı',
                'norm_kadro': ''
            })
    save_assignments(df)
    return atama_kayitlari, subeler

# Çoklu atama endpointi
def assign_employees(assignments, subeler, sube_ad_column='ad', sube_adres_column='adres'):
    df = load_assignments()
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
    for atama in assignments:
        calisan_adi = atama['calisan_adi']
        calisan_adresi = atama['calisan_adresi']
        tckn = atama.get('tckn', '')
        sube_adi = atama['sube_adi']
        sube_adres = atama['sube_adres']
        mesafe = atama.get('mesafe', '')
        sure = atama.get('sure', '')
        # Mesafe ve süreyi uygun şekilde yuvarla
        try:
            mesafe = round(float(mesafe), 2) if mesafe not in [None, ''] else ''
        except:
            mesafe = ''
        try:
            sure = int(round(float(sure))) if sure not in [None, ''] else ''
        except:
            sure = ''
        # Zaten aynı atama var mı kontrol et
        exists = ((df['Çalışan Adı'] == calisan_adi) &
                  (df['Çalışan Adresi'] == calisan_adresi) &
                  (df['Şube Adı'] == sube_adi) &
                  (df['Şube Adresi'] == sube_adres)).any()
        if exists:
            continue  # Aynı atama varsa ekleme
        # Normu güncelle (arttır)
        subeler = update_branch_value(sube_adi, sube_adres, 1, subeler, key='norm', ad_col=sube_ad_column, adres_col=sube_adres_column)
        # Güncel normu bul
        norm = None
        for sube in subeler:
            if sube.get(sube_ad_column) == sube_adi and sube.get(sube_adres_column) == sube_adres:
                norm = sube.get('norm', 0)
        # Atamayı ekle (append yerine concat kullan)
        new_row = pd.DataFrame([{
            'TCKN': tckn,
            'Çalışan Adı': calisan_adi,
            'Çalışan Adresi': calisan_adresi,
            'Şube Adı': sube_adi,
            'Şube Adresi': sube_adres,
            'Mesafe (km)': mesafe,
            'Süre (dk)': sure,
            'Atama Tarihi': now,
            'Norm': norm
        }])
        df = pd.concat([df, new_row], ignore_index=True)
    save_assignments(df)
    return subeler

# Atamaları listele
@app.route('/assignments', methods=['GET'])
@login_required
def list_assignments():
    df = load_assignments()
    # Sütun sırasını ayarla: TCKN, Çalışan Adı, ...
    columns = ['TCKN', 'Çalışan Adı', 'Çalışan Adresi', 'Şube Adı', 'Şube Adresi', 'Mesafe (km)', 'Süre (dk)', 'Atama Tarihi', 'Norm']
    if all(col in df.columns for col in columns):
        df = df[columns]
    return df.to_json(orient='records', force_ascii=False)

# Atama yap (çoklu)
@app.route('/assign', methods=['POST'])
@login_required
def assign():
    try:
        data = request.json
        assignments = data.get('assignments', [])  # [{'calisan_adi':..., 'calisan_adresi':..., 'sube_adi':..., 'sube_adres':...}, ...]
        subeler = data.get('subeler', [])
        sube_ad_column = data.get('sube_ad_column', 'ad')
        sube_adres_column = data.get('sube_adres_column', 'adres')
        subeler = assign_employees(assignments, subeler, sube_ad_column, sube_adres_column)
        return jsonify({'status': 'success', 'subeler': subeler})
    except Exception as e:
        print("Atama hatası:", e)
        return jsonify({'error': str(e)}), 500

# Atama iptal et (tekli)
@app.route('/unassign', methods=['POST'])
@login_required
def unassign():
    try:
        data = request.json
        calisan_adi = data.get('calisan_adi')
        sube_adi = data.get('sube_adi')
        sube_adresi = data.get('sube_adres')
        subeler = data.get('subeler', [])
        sube_ad_column = data.get('sube_ad_column', 'ad')
        sube_adres_column = data.get('sube_adres_column', 'adres')
        df = load_assignments()
        # Güvenli string dönüşümü
        def safe_str(val):
            if val is None:
                return ""
            s = str(val).replace('\n', ' ').replace('\r', ' ')
            s = re.sub(r'\s+', ' ', s)  # Birden fazla boşluğu teke indir
            return s.strip().lower()
        # Son atamayı bul ve sil
        idx = df[
            (df['Çalışan Adı'].apply(safe_str) == safe_str(calisan_adi)) &
            (df['Şube Adı'].apply(safe_str) == safe_str(sube_adi)) &
            (df['Şube Adresi'].apply(safe_str) == safe_str(sube_adresi))
        ].index
        if not idx.empty:
            df = remove_row_from_df(df, lambda row: (row['Çalışan Adı'] == calisan_adi) and (row['Şube Adı'] == sube_adi) and (row['Şube Adresi'] == sube_adresi))
            save_assignments(df)
            # Normu geri azalt
            subeler = update_branch_value(sube_adi, sube_adresi, -1, subeler, key='norm', ad_col=sube_ad_column, adres_col=sube_adres_column)
            return jsonify({'status': 'success', 'subeler': subeler})
        else:
            return jsonify({'status': 'fail', 'message': 'Atama bulunamadı'})
    except Exception as e:
        print("Atama iptal hatası:", e)
        return jsonify({'error': str(e)}), 500

@app.route('/download_assignments', methods=['GET'])
@login_required
def download_assignments():
    try:
        return send_file(ASSIGNMENTS_FILE, as_attachment=True, download_name='atama_listesi.xlsx')
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/update_branch_norms_from_assignments', methods=['POST'])
@login_required
def update_branch_norms_from_assignments():
    try:
        subeler = request.json.get('subeler', [])
        sube_ad_column = request.json.get('sube_ad_column', 'ad')
        sube_adres_column = request.json.get('sube_adres_column', 'adres')
        df = load_assignments()
        # Her şubenin en güncel normunu bul
        norm_map = {}
        for _, row in df.iterrows():
            key = (row['Şube Adı'], row['Şube Adresi'])
            norm_map[key] = row['Norm']
        # Subeler listesini güncelle
        for sube in subeler:
            key = (sube.get(sube_ad_column), sube.get(sube_adres_column))
            if key in norm_map:
                sube['norm'] = norm_map[key]
        return jsonify({'status': 'success', 'subeler': subeler})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/assignments_page')
@login_required
def assignments_page():
    return render_template('assignments.html')

@app.route('/delete_all_assignments', methods=['POST'])
@login_required
def delete_all_assignments():
    try:
        df = pd.DataFrame(columns=[
            'TCKN', 'Çalışan Adı', 'Çalışan Adresi', 'Şube Adı', 'Şube Adresi', 'Atama Tarihi', 'Norm'
        ])
        save_assignments(df)
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/update_assignment', methods=['POST'])
@login_required
def update_assignment():
    try:
        data = request.json
        old = data.get('old', {})
        new = data.get('new', {})
        df = load_assignments()
        # Güvenli string dönüşümü
        def safe_str(val):
            if val is None:
                return ""
            s = str(val).replace('\n', ' ').replace('\r', ' ')
            s = re.sub(r'\s+', ' ', s)
            return s.strip().lower()
        # Eski kaydı bul
        idx = df[
            (df['Çalışan Adı'].apply(safe_str) == safe_str(old.get('calisan_adi')))
            & (df['Çalışan Adresi'].apply(safe_str) == safe_str(old.get('calisan_adresi')))
            & (df['Şube Adı'].apply(safe_str) == safe_str(old.get('sube_adi')))
            & (df['Şube Adresi'].apply(safe_str) == safe_str(old.get('sube_adres')))
        ].index
        if not idx.empty:
            # Sadece ilkini güncelle (tekli satır)
            i = idx[0]
            df = update_row_in_df(df, lambda row: (row['Çalışan Adı'] == old.get('calisan_adi')) and (row['Çalışan Adresi'] == old.get('calisan_adresi')) and (row['Şube Adı'] == old.get('sube_adi')) and (row['Şube Adresi'] == old.get('sube_adres')), {'Çalışan Adı': new.get('calisan_adi', '')})
            df = update_row_in_df(df, lambda row: (row['Çalışan Adı'] == new.get('calisan_adi', '')) and (row['Çalışan Adresi'] == new.get('calisan_adresi', '')) and (row['Şube Adı'] == new.get('sube_adi', '')) and (row['Şube Adresi'] == new.get('sube_adres', '')), {'Çalışan Adı': new.get('calisan_adi', ''), 'Çalışan Adresi': new.get('calisan_adresi', ''), 'Şube Adı': new.get('sube_adi', ''), 'Şube Adresi': new.get('sube_adres', '')})
            save_assignments(df)
            return jsonify({'status': 'success'})
        else:
            return jsonify({'status': 'fail', 'error': 'Kayıt bulunamadı'})
    except Exception as e:
        print("Atama güncelleme hatası:", e)
        return jsonify({'status': 'fail', 'error': str(e)})

def get_transit_steps(origin, destination):
    url = (
        f"https://maps.googleapis.com/maps/api/directions/json?origin={origin}&destination={destination}"
        f"&mode=transit&key={GOOGLE_MAPS_API_KEY}&language=tr"
    )
    response = requests.get(url)
    data = response.json()
    steps = []
    if data.get('status') == 'OK' and data['routes']:
        for leg in data['routes'][0]['legs']:
            for step in leg['steps']:
                step_info = {
                    'travel_mode': step.get('travel_mode'),
                    'instruction': step.get('html_instructions', ''),
                    'duration': step.get('duration', {}).get('text', ''),
                    'distance': step.get('distance', {}).get('text', ''),
                }
                if step.get('transit_details'):
                    td = step['transit_details']
                    step_info['line'] = td.get('line', {}).get('short_name', '')
                    step_info['vehicle'] = td.get('line', {}).get('vehicle', {}).get('name', '')
                    step_info['departure_stop'] = td.get('departure_stop', {}).get('name', '')
                    step_info['arrival_stop'] = td.get('arrival_stop', {}).get('name', '')
                    step_info['num_stops'] = td.get('num_stops', '')
                steps.append(step_info)
    return steps

@app.route('/toplu_tasima', methods=['GET', 'POST'])
@login_required
def toplu_tasima():
    rotalar = []
    calisan_adresi = request.args.get('calisan_adresi', '') or ''
    sube_adresleri = request.args.get('sube_adresleri', '') or ''
    if request.method == 'POST':
        calisan_adresi = request.form.get('calisan_adresi', '').strip()
        sube_adresleri = request.form.get('sube_adresleri', '').strip()
    sube_adres_list = [adres.strip() for adres in sube_adresleri.split(',') if adres.strip()]
    # Şube adreslerinden koordinatları bul
    sube_coords = []
    for adres in sube_adres_list:
        coords = get_coordinates_cached(adres)
        if coords:
            sube_coords.append({'adres': adres, 'lat': coords[0], 'lon': coords[1]})
    # Çalışan adresi koordinatı
    calisan_coords = get_coordinates_cached(calisan_adresi)
    if calisan_coords and sube_coords:
        # En yakın 3 şubeyi bul
        for sube in sube_coords:
            sube['mesafe'] = haversine(calisan_coords[0], calisan_coords[1], sube['lat'], sube['lon'])
        yakinlar = sorted(sube_coords, key=lambda x: x['mesafe'])[:3]
        for sube in yakinlar:
            # Mesafe ve süreyi al
            mesafe_sure = get_distance_and_duration_batch(f"{calisan_coords[0]},{calisan_coords[1]}", [(sube['lat'], sube['lon'])])
            mesafe = mesafe_sure[0]['distance'] if mesafe_sure and mesafe_sure[0] else 0
            sure = round(mesafe_sure[0]['duration']) if mesafe_sure and mesafe_sure[0] else 0
            # Transit adımlarını çek
            steps = get_transit_steps(calisan_adresi, sube['adres'])
            rotalar.append({
                'calisan_adresi': calisan_adresi,
                'sube_adi': '',
                'sube_adres': sube['adres'],
                'mesafe': round(mesafe, 2),
                'sure': sure,
                'steps': steps
            })
    return render_template('toplu_tasima.html', rotalar=rotalar, calisan_adresi=calisan_adresi, sube_adresleri=sube_adresleri, google_maps_api_key=GOOGLE_MAPS_API_KEY)

@app.route('/save_bulk_assignments', methods=['POST'])
@login_required
def save_bulk_assignments_endpoint():
    try:
        data = request.json
        assignments = data.get('assignments', [])  # [{'calisan_adi':..., 'calisan_adresi':..., 'yakin_subeler':[...]}]
        subeler = data.get('subeler', [])
        n = int(data.get('n', 3))
        sube_ad_column = data.get('sube_ad_column', 'ad')
        sube_adres_column = data.get('sube_adres_column', 'adres')
        # Aynı çalışan birden fazla kez var mı kontrol et
        seen = set()
        for atama in assignments:
            key = (atama.get('calisan_adi'), atama.get('calisan_adresi'))
            if key in seen:
                return jsonify({'status': 'fail', 'error': 'Aynı çalışan için birden fazla atama seçtiniz. Lütfen her çalışan için yalnızca bir atama yapınız.'}), 400
            seen.add(key)
        # norm_kadro alanı yoksa norm'dan başlat
        for sube in subeler:
            if 'norm_kadro' not in sube:
                sube['norm_kadro'] = sube.get('norm', 0)
        atama_kayitlari, guncel_subeler = save_bulk_assignments(assignments, subeler, n, sube_ad_column, sube_adres_column)
        return jsonify({'status': 'success', 'atama_kayitlari': atama_kayitlari, 'subeler': guncel_subeler})
    except Exception as e:
        print("Toplu atama kaydetme hatası:", e)
        return jsonify({'error': str(e)}), 500

def add_row_to_df(df, row_dict):
    """DataFrame'e yeni bir satır ekler."""
    new_row = pd.DataFrame([row_dict])
    return pd.concat([df, new_row], ignore_index=True)

def remove_row_from_df(df, condition_func):
    """Koşula uyan satırları DataFrame'den siler."""
    idx = df[ df.apply(condition_func, axis=1) ].index
    return df.drop(idx)

def update_row_in_df(df, condition_func, update_dict):
    """Koşula uyan ilk satırı günceller."""
    idx = df[ df.apply(condition_func, axis=1) ].index
    if not idx.empty:
        i = idx[0]
        for key, value in update_dict.items():
            df.at[i, key] = value
    return df

if __name__ == '__main__':
    app.run(debug=True)