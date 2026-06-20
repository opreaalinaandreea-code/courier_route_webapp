import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from math import radians, sin, cos, sqrt, atan2
from functools import lru_cache
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter

st.set_page_config(page_title="Courier Route Web App", layout="wide")
st.title("Courier Route Web App")
st.caption("Configure orders, couriers and generate routes online.")

USER_AGENT = 'courier-route-webapp-romania'
geolocator = Nominatim(user_agent=USER_AGENT, timeout=10)
geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1, swallow_exceptions=True)
DEFAULT_START = datetime.strptime('10:00', '%H:%M')
BUFFER_MIN = 10
MAX_LIVRARI = 20
SLOT_MINUTES = 120

@lru_cache(maxsize=5000)
def geocode_address(addr):
    if addr is None or str(addr).strip() == '':
        return None, None, None
    loc = geocode(f"{addr}, Romania", country_codes='ro')
    if loc is None:
        return None, None, None
    return loc.latitude, loc.longitude, loc.address

def read_file(uploaded):
    if uploaded is None:
        return None
    if uploaded.name.lower().endswith('.csv'):
        return pd.read_csv(uploaded)
    return pd.read_excel(uploaded)

def haversine(lat1, lon1, lat2, lon2):
    if any(pd.isna(v) for v in [lat1, lon1, lat2, lon2]):
        return None
    R = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    return 2 * R * atan2(sqrt(a), sqrt(1-a))

def make_slot(dt):
    minutes = dt.hour * 60 + dt.minute
    if minutes < 600:
        minutes = 600
    idx = (minutes - 600) // SLOT_MINUTES
    start = 600 + idx * SLOT_MINUTES
    s = datetime(2000,1,1) + timedelta(minutes=start)
    e = s + timedelta(minutes=SLOT_MINUTES)
    return f"{s.strftime('%H:%M')}-{e.strftime('%H:%M')}"

def nearest_neighbor_route(df_orders, start_lat, start_lon):
    remaining = df_orders.copy().reset_index(drop=True)
    ordered = []
    cur_lat, cur_lon = start_lat, start_lon
    while len(remaining):
        remaining['dist'] = remaining.apply(lambda r: haversine(cur_lat, cur_lon, r['Latitudine'], r['Longitudine']) if pd.notna(r['Latitudine']) and pd.notna(r['Longitudine']) else 1e9, axis=1)
        idx = remaining['dist'].idxmin()
        row = remaining.loc[idx].copy()
        ordered.append(row)
        cur_lat, cur_lon = row['Latitudine'], row['Longitudine']
        remaining = remaining.drop(idx).reset_index(drop=True)
    return pd.DataFrame(ordered)

def estimate_route_minutes(route_df):
    if route_df is None or len(route_df) == 0:
        return 0.0
    stops = pd.to_numeric(route_df.get('Durata_stop_min', 10), errors='coerce').fillna(10)
    return float((stops + BUFFER_MIN).sum())

def rebalance_routes(routes_by_courier):
    changed = True
    while changed:
        changed = False
        totals = {k: estimate_route_minutes(v) for k, v in routes_by_courier.items() if len(v)}
        if len(totals) < 2:
            break
        slow = max(totals, key=totals.get)
        fast = min(totals, key=totals.get)
        if totals[slow] - totals[fast] < 30:
            break
        if len(routes_by_courier[slow]) <= 1 or len(routes_by_courier[fast]) >= MAX_LIVRARI:
            break
        candidate = routes_by_courier[slow].iloc[-1:]
        routes_by_courier[slow] = routes_by_courier[slow].iloc[:-1].reset_index(drop=True)
        routes_by_courier[fast] = pd.concat([routes_by_courier[fast], candidate], ignore_index=True)
        changed = True
    return routes_by_courier

st.sidebar.header('Controale')
mode = st.sidebar.radio('Tip input', ['Upload fișier', 'Date de test'])

if mode == 'Upload fișier':
    orders_file = st.sidebar.file_uploader('Orders file', type=['csv', 'xlsx'])
    couriers_file = st.sidebar.file_uploader('Couriers file', type=['csv', 'xlsx'])
else:
    orders_file = None
    couriers_file = None

if mode == 'Date de test':
    st.subheader('Date de test')
    c1, c2 = st.columns(2)
    with c1:
        st.write('Orders')
        orders = pd.DataFrame([
            {'ID_Livrare': 1, 'Client': 'Client A', 'Adresa_originala': 'Bucuresti, Unirii, 10', 'Latitudine': 44.4268, 'Longitudine': 26.1025, 'Durata_stop_min': 10, 'Status_confirmare_client': 'Neconfirmat'},
            {'ID_Livrare': 2, 'Client': 'Client B', 'Adresa_originala': 'Bucuresti, Calea Victoriei, 20', 'Latitudine': 44.4320, 'Longitudine': 26.0970, 'Durata_stop_min': 10, 'Status_confirmare_client': 'Neconfirmat'},
            {'ID_Livrare': 3, 'Client': 'Client C', 'Adresa_originala': 'Otopeni, Eroilor, 5', 'Latitudine': 44.5500, 'Longitudine': 26.0700, 'Durata_stop_min': 10, 'Status_confirmare_client': 'Neconfirmat'},
            {'ID_Livrare': 4, 'Client': 'Client D', 'Adresa_originala': 'Bragadiru, Prelungirea Ghencea, 47', 'Latitudine': 44.3790, 'Longitudine': 25.9980, 'Durata_stop_min': 10, 'Status_confirmare_client': 'Neconfirmat'}
        ])
        st.dataframe(orders, use_container_width=True)
    with c2:
        st.write('Couriers')
        couriers = pd.DataFrame([
            {'Nume_curier': 'Curier 1', 'Ora_plecare': '08:00', 'Capacitate_max_livrari': 20, 'Punct_plecare_Latitudine': 44.4268, 'Punct_plecare_Longitudine': 26.1025, 'Punct_finalizare_Latitudine': 44.4268, 'Punct_finalizare_Longitudine': 26.1025, 'Activ': 'DA'},
            {'Nume_curier': 'Curier 2', 'Ora_plecare': '08:00', 'Capacitate_max_livrari': 20, 'Punct_plecare_Latitudine': 44.5500, 'Punct_plecare_Longitudine': 26.0700, 'Punct_finalizare_Latitudine': 44.5500, 'Punct_finalizare_Longitudine': 26.0700, 'Activ': 'DA'}
        ])
        st.dataframe(couriers, use_container_width=True)
else:
    orders = read_file(orders_file)
    couriers = read_file(couriers_file)
    if orders is not None and couriers is not None:
     st.subheader('Mapare coloane')
     ocols = list(orders.columns)
     ccols = list(couriers.columns)
     col1, col2 = st.columns(2)
    with col1:
        order_address_col = st.selectbox('Coloana adresă comenzi', ocols, index=ocols.index('Adresa_originala') if 'Adresa_originala' in ocols else 0)
        order_client_col = st.selectbox('Coloana client comenzi', ocols, index=ocols.index('Client') if 'Client' in ocols else 0)
    with col2:
        courier_name_col = st.selectbox('Coloana nume curier', ccols, index=ccols.index('Nume_curier') if 'Nume_curier' in ccols else 0)
        courier_start_col = st.selectbox('Coloana punct plecare', ccols, index=ccols.index('Punct_plecare') if 'Punct_plecare' in ccols else 0) if 'Punct_plecare' in ccols else None

    orders = orders.copy().reset_index(drop=True)
    couriers = couriers.copy().reset_index(drop=True)
    if order_address_col != 'Adresa_originala':
        orders['Adresa_originala'] = orders[order_address_col].astype(str)
    if order_client_col != 'Client':
        orders['Client'] = orders[order_client_col].astype(str)
    if courier_name_col != 'Nume_curier':
        couriers['Nume_curier'] = couriers[courier_name_col].astype(str)
    if courier_start_col is not None and courier_start_col != 'Punct_plecare':
        couriers['Punct_plecare'] = couriers[courier_start_col].astype(str)
    if 'ID_Livrare' not in orders.columns:
        orders['ID_Livrare'] = range(1, len(orders) + 1)
    for col in ['Latitudine', 'Longitudine']:
        if col not in orders.columns:
            orders[col] = None
    if 'Durata_stop_min' not in orders.columns:
        orders['Durata_stop_min'] = 10
    if 'Status_confirmare_client' not in orders.columns:
        orders['Status_confirmare_client'] = 'Neconfirmat'
    if 'Geocoded_address' not in orders.columns:
        orders['Geocoded_address'] = None

    address_col = None
    for c in ['Adresa_originala', 'Adresa', 'Address']:
        if c in orders.columns:
            address_col = c
            break
    if address_col is None:
        st.error('Lipseste coloana de adresa. Foloseste Adresa_originala sau Adresa.')
        st.stop()
    if address_col != 'Adresa_originala':
        orders['Adresa_originala'] = orders[address_col].astype(str)

    with st.spinner('Geocoding addresses...'):
        for idx, row in orders[orders['Latitudine'].isna() | orders['Longitudine'].isna()].iterrows():
            addr = row.get('Adresa_originala', row.get(address_col, ''))
            lat, lon, full = geocode_address(addr)
            orders.at[idx, 'Latitudine'] = lat
            orders.at[idx, 'Longitudine'] = lon
            orders.at[idx, 'Geocoded_address'] = full

    orders['Latitudine'] = pd.to_numeric(orders['Latitudine'], errors='coerce')
    orders['Longitudine'] = pd.to_numeric(orders['Longitudine'], errors='coerce')
    orders['Durata_stop_min'] = pd.to_numeric(orders['Durata_stop_min'], errors='coerce').fillna(10)

    couriers['Ora_plecare_parsata'] = pd.to_datetime(couriers['Ora_plecare'].astype(str), format='%H:%M', errors='coerce')
    couriers['Capacitate_max_livrari'] = pd.to_numeric(couriers['Capacitate_max_livrari'], errors='coerce').fillna(MAX_LIVRARI).astype(int)
    if 'Activ' in couriers.columns:
        couriers = couriers[couriers['Activ'].astype(str).str.upper().isin(['DA', '1', 'TRUE', 'YES'])]
    couriers = couriers.reset_index(drop=True)
    couriers['assigned'] = [[] for _ in range(len(couriers))]
    couriers['load_minutes'] = 0.0

    courier_points = []
    for _, r in couriers.iterrows():
        try:
            courier_points.append((float(r.get('Punct_plecare_Latitudine')), float(r.get('Punct_plecare_Longitudine')), float(r.get('Punct_finalizare_Latitudine')), float(r.get('Punct_finalizare_Longitudine'))))
        except Exception:
            courier_points.append((None, None, None, None))

    def route_score(order_row, courier_idx):
        slat, slon, flat, flon = courier_points[courier_idx]
        lat, lon = order_row['Latitudine'], order_row['Longitudine']
        score = 0
        if slat is not None:
            score += haversine(slat, slon, lat, lon) or 0
        if flat is not None:
            score += haversine(lat, lon, flat, flon) or 0
        score += len(couriers.at[courier_idx, 'assigned']) * 0.7
        score += couriers.at[courier_idx, 'load_minutes'] / 60.0 * 0.3
        return score

    for _, order in orders.iterrows():
        best_idx = None
        best_score = None
        for ci in range(len(couriers)):
            if len(couriers.at[ci, 'assigned']) >= int(couriers.at[ci, 'Capacitate_max_livrari']):
                continue
            sc = route_score(order, ci)
            if best_score is None or sc < best_score:
                best_score = sc
                best_idx = ci
        if best_idx is None:
            continue
        couriers.at[best_idx, 'assigned'].append(int(order['ID_Livrare']))
        couriers.at[best_idx, 'load_minutes'] += float(order.get('Durata_stop_min', 10)) + BUFFER_MIN
        orders.loc[order.name, 'Curier_alocat'] = couriers.at[best_idx, 'Nume_curier']
        orders.loc[order.name, 'Status'] = 'Alocat'

    routes_by_courier = {}
    for _, crow in couriers.iterrows():
        ids = crow['assigned']
        sub = orders[orders['ID_Livrare'].isin(ids)].copy()
        try:
            slat = float(crow.get('Punct_plecare_Latitudine')); slon = float(crow.get('Punct_plecare_Longitudine'))
        except Exception:
            slat = slon = None
        if slat is not None and len(sub):
            sub = nearest_neighbor_route(sub, slat, slon)
        routes_by_courier[crow['Nume_curier']] = sub.reset_index(drop=True)

    routes_by_courier = rebalance_routes(routes_by_courier)

    out_rows = []
    for _, crow in couriers.iterrows():
        name = crow['Nume_curier']
        current = crow['Ora_plecare_parsata'] if pd.notna(crow['Ora_plecare_parsata']) else DEFAULT_START
        sec = 1
        for _, orow in routes_by_courier.get(name, pd.DataFrame()).iterrows():
            current = current + timedelta(minutes=float(orow.get('Durata_stop_min', 10)))
            out_rows.append({
                'Curier': name,
                'Secventa': sec,
                'ID_Livrare': orow.get('ID_Livrare'),
                'Client': orow.get('Client', ''),
                'Adresa_originala': orow.get('Adresa_originala', ''),
                'Ora_estimata_sosire': current.strftime('%H:%M'),
                'Slot_fix_livrare': make_slot(current),
                'Status_confirmare_client': orow.get('Status_confirmare_client', 'Neconfirmat')
            })
            current = current + timedelta(minutes=BUFFER_MIN)
            sec += 1
                routes = pd.DataFrame(out_rows)
    export_df = routes.merge(orders, on='ID_Livrare', how='left', suffixes=('', '_original'))
    export_df = export_df[['Curier', 'Secventa', 'ID_Livrare'] + [c for c in orders.columns if c != 'ID_Livrare'] + ['Ora_estimata_sosire', 'Slot_fix_livrare', 'Status_confirmare_client']] if len(routes) else routes
    st.subheader('Rezumat curieri')
    st.dataframe(pd.DataFrame({
        'Curier': couriers['Nume_curier'],
        'Livrari': couriers['assigned'].apply(len),
        'Minute_estimate': couriers['load_minutes'].round(0)
    }), use_container_width=True)
    st.subheader('Trasee')
    st.dataframe(routes, use_container_width=True)
    st.download_button('Download routes CSV', export_df.to_csv(index=False).encode('utf-8-sig'), 'routes_output.csv', 'text/csv')
else:
    st.info('Incarca sau selecteaza date de test pentru a genera traseele.')
