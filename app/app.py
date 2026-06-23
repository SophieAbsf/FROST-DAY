import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date

# Import direct sans préfixe "app." car les fichiers partagent le même répertoire
from utils import get_city_coordinates, find_closest_valid_station, calculate_frost_stats

st.set_page_config(page_title="Défi Frost Days", page_icon="❄️", layout="wide")

st.title("❄️ Application Frost Days")
st.write("Analyse des indicateurs de jours de gel en temps réel pour une commune donnée.")

# Chargement ou génération des données de référence (Communes et Stations) 
@st.cache_data
def load_reference_data():
    # Note : Vous pouvez remplacer ce mock par pd.read_csv("votre_fichier.csv")
    df_communes = pd.DataFrame({
        'nom_commune': ['Paris', 'Marseille', 'Lyon', 'Culey', 'Bihorel'],
        'code_departement': ['75', '13', '69', '55', '76'],
        'latitude': [48.866, None, 45.75, 48.755, 49.4542], 
        'longitude': [2.333, None, 4.85, 5.266, 1.1162]
    })
    
    df_stations = pd.DataFrame({
        'id_station': [75001, 13002, 69003, 55004],
        'latitude': [48.85, 43.30, 45.76, 48.75],
        'longitude': [2.35, 5.40, 4.83, 5.25]
    })
    return df_communes, df_stations

df_communes, df_stations = load_reference_data()

# Formulaire utilisateur (Barre latérale) 
st.sidebar.header("Paramètres de recherche")
commune_input = st.sidebar.text_input("Nom de la commune", value="Paris")
dept_input = st.sidebar.text_input("Département", value="75")

# Plage de dates de référence recommandée 
start_date = st.sidebar.date_input("Date de début", date(2014, 1, 1))
end_date = st.sidebar.date_input("Date de fin", date(2023, 12, 31))

if st.sidebar.button("Lancer l'analyse"):
    if commune_input and dept_input:
        
        # 1. Récupération des coordonnées GPS de la commune
        lat, lon = get_city_coordinates(df_communes, commune_input, dept_input)
        
        if lat is None or lon is None:
            st.error(f"❌ Impossible de localiser la commune '{commune_input}' ({dept_input}).")
        else:
            st.info(f"📍 Ville localisée : Latitude {lat:.4f}, Longitude {lon:.4f}")
            
            # 2. Recherche en temps réel de la station la plus proche et valide
            with st.spinner("Recherche de la station la plus proche (< 35% de données manquantes)..."):
                id_station, df_meteo, missing_pct = find_closest_valid_station(df_stations, lat, lon, start_date, end_date)
                
            if id_station is None:
                st.error("❌ Aucune station valide n'a été trouvée à proximité sous le seuil requis de données.")
            else:
                st.success(f"🎯 Station sélectionnée : ID {id_station} ({missing_pct:.1f}% de données manquantes)")
                
                # 3. Calcul de l'ensemble des statistiques de gel 
                total_frost, avg_frost, stats_day = calculate_frost_stats(df_meteo)
                
                # 4. Affichage des indicateurs de performance clés (KPI) 
                st.subheader(f"📊 Statistiques de Gel pour {commune_input}")
                col1, col2 = st.columns(2)
                col1.metric("Nombre total de jours de gel", value=total_frost)
                col2.metric("Moyenne annuelle", value=f"{avg_frost:.2f} jours/an")
                
                # 5. Graphique interactif (Valeurs relatives %) 
                st.markdown("---")
                st.subheader("📅 Risque historique de gel par jour de l'année (%)")
                
                fig = px.bar(
                    stats_day,
                    x='month_day',
                    y='relatif',
                    title="Probabilité d'avoir un jour de gel sur la période sélectionnée",
                    labels={'month_day': "Date (MM-JJ)", 'relatif': "Fréquence de gel (%)"},
                    color_discrete_sequence=['#3399FF']
                )
                st.plotly_chart(fig, use_container_width=True)
                
                # 6. Tableau complet des données brutes 
                with st.expander("Consulter le tableau détaillé (Valeurs Absolues et Relatives)"):
                    st.dataframe(stats_day[['month_day', 'absolu', 'relatif']].rename(
                        columns={'month_day': 'Jour', 'absolu': 'Total Absolu (Occurrences)', 'relatif': 'Taux Relatif (%)'}
                    ))
    else:
        st.warning("⚠️ Veuillez renseigner le nom de la commune et son département.")