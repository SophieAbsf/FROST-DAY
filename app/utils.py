import numpy as np
import pandas as pd

# Dictionnaire officiel pour pallier les coordonnées manquantes
MISSING_CITIES_GPS = {
    "Marseille": [43.295, 5.3721],
    "Paris": [48.866, 2.333],
    "Culey": [48.755, 5.266],
    "Les Hauts-Talican": [49.3436, 2.01931],
    "Lyon": [45.75, 4.85],
    "Bihorel": [49.4542, 1.1162],
    "Saint-Lucien": [48.6480, 1.6229],
    "L'Oie": [46.7982, -1.1302],
    "Sainte-Florence": [46.7965, -1.1520]
}

def haversine_distance(lat1, lon1, lat2, lon2):
    """Calcule la distance en kilomètres entre deux points géographiques (Haversine)."""
    R = 6371.0
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
    c = 2 * np.arcsin(np.sqrt(a))
    return R * c

def get_city_coordinates(df_communes, nom_commune, departement):
    """Trouve la latitude et la longitude d'une commune."""
    df_clean = df_communes.copy()
    df_clean['nom_commune'] = df_clean['nom_commune'].astype(str).str.lower().str.strip()
    df_clean['code_departement'] = df_clean['code_departement'].astype(str).str.strip()
    
    target_city = str(nom_commune).lower().strip()
    target_dept = str(departement).strip()
    
    row = df_clean[(df_clean['nom_commune'] == target_city) & (df_clean['code_departement'] == target_dept)]
    
    if row.empty:
        # Fallback sur le dictionnaire de secours
        for city, coords in MISSING_CITIES_GPS.items():
            if city.lower() == target_city:
                return coords[0], coords[1]
        return None, None
        
    lat = row.iloc[0].get('latitude')
    lon = row.iloc[0].get('longitude')
    
    # Remplacement si la valeur est NaN dans le fichier des communes
    if pd.isna(lat) or pd.isna(lon):
        city_name = row.iloc[0]['nom_commune']
        for city, coords in MISSING_CITIES_GPS.items():
            if city.lower() == str(city_name).lower():
                return coords[0], coords[1]
                
    return lat, lon

def get_station_data_simulated(id_station, start_date, end_date):
    """Génère de manière déterministe les données de température minimale (TN) pour une station."""
    dates = pd.date_range(start=start_date, end=end_date, freq="D")
    np.random.seed(int(id_station) % 10000)
    
    # Variations saisonnières réalistes de la température minimale
    months = dates.month
    base_temp = {1: -2, 2: -1, 3: 3, 4: 6, 5: 10, 6: 13, 7: 15, 8: 15, 9: 11, 10: 7, 11: 3, 12: -1}
    tn_values = [base_temp[m] + np.random.uniform(-5, 5) for m in months]
    
    df = pd.DataFrame({'date': dates, 'TN': tn_values})
    
    # Simulation de 5% de valeurs manquantes pour valider l'algorithme de contrôle
    mask = np.random.choice([True, False], size=len(df), p=[0.05, 0.95])
    df.loc[mask, 'TN'] = np.nan
    return df

def find_closest_valid_station(df_stations, city_lat, city_lon, start_date, end_date):
    """Calcule la distance avec Haversine et retourne la station valide la plus proche (< 35% de manquants)."""
    df_temp = df_stations.dropna(subset=['latitude', 'longitude']).copy()
    df_temp['distance'] = haversine_distance(city_lat, city_lon, df_temp['latitude'], df_temp['longitude'])
    df_temp_sorted = df_temp.sort_values(by='distance')
    
    total_days = (pd.to_datetime(end_date) - pd.to_datetime(start_date)).days + 1
    
    for _, station in df_temp_sorted.iterrows():
        id_station = station['id_station']
        df_meteo = get_station_data_simulated(id_station, start_date, end_date)
        
        # Validation de la règle des 35% de valeurs manquantes
        missing_count = total_days - df_meteo['TN'].count()
        missing_pct = (missing_count / total_days) * 100
        
        if missing_pct <= 35:
            return id_station, df_meteo, missing_pct
            
    return None, None, 100.0

def calculate_frost_stats(df_meteo):
    """Calcule le total, la moyenne annuelle, et les stats par jour de l'année (hors 29 février)."""
    df = df_meteo.copy()
    df['date'] = pd.to_datetime(df['date'])
    df['year'] = df['date'].dt.year
    df['month_day'] = df['date'].dt.strftime('%m-%d')
    
    # Jour de gel défini par une température minimale (TN) <= 0°C
    df['is_frost'] = df['TN'] <= 0.0
    
    total_frost_days = int(df['is_frost'].sum())
    years_count = df['year'].nunique()
    avg_frost_per_year = float(total_frost_days / years_count) if years_count > 0 else 0.0
    
    # Filtrer le 29 février pour les statistiques journalières récurrentes
    df_no_leap = df[df['month_day'] != '02-29'].copy()
    
    frost_by_day = df_no_leap.groupby('month_day')['is_frost'].sum().reset_index(name='absolu')
    total_years_by_day = df_no_leap.groupby('month_day')['year'].nunique().reset_index(name='total_years')
    
    stats_day = pd.merge(frost_by_day, total_years_by_day, on='month_day')
    stats_day['relatif'] = (stats_day['absolu'] / stats_day['total_years']) * 100
    
    return total_frost_days, avg_frost_per_year, stats_day