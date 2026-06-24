from __future__ import annotations

from datetime import date

import plotly.express as px
import streamlit as st

from frost_days.config import configure_logging
from frost_days.departments import department_options, parse_department_option
from frost_days.geo_api import Commune, list_communes
from frost_days.public_data_client import PublicMeteoFranceClient
from frost_days.stations import select_first_valid_station
from frost_days.statistics import compute_statistics

configure_logging()

st.set_page_config(page_title="Frost Days", layout="wide")
st.title("Frost Days")

MIN_ALLOWED_DATE = date(2013, 1, 1)
MAX_ALLOWED_DATE = date(2024, 12, 31)


@st.cache_data(show_spinner=False)
def cached_communes(department_code: str) -> list[Commune]:
    return list_communes(department_code)


department_choice = st.sidebar.selectbox(
    "Departement",
    options=department_options(),
    index=20,
)
department = parse_department_option(department_choice)

try:
    communes = cached_communes(department)
except Exception as exc:
    st.sidebar.error(f"Impossible de charger les communes: {exc}")
    st.stop()

commune_labels = [f"{commune.name} ({commune.code})" for commune in communes]
default_index = next(
    (index for index, commune in enumerate(communes) if commune.name.casefold() == "dijon"),
    0,
)

with st.sidebar.form("frost-days-form"):
    st.header("Recherche")
    commune_index = st.selectbox(
        "Commune",
        options=range(len(communes)),
        index=default_index,
        format_func=lambda index: commune_labels[index],
    )
    start_date = st.date_input(
        "Date de debut",
        MIN_ALLOWED_DATE,
        min_value=MIN_ALLOWED_DATE,
        max_value=MAX_ALLOWED_DATE,
    )
    end_date = st.date_input(
        "Date de fin",
        MAX_ALLOWED_DATE,
        min_value=MIN_ALLOWED_DATE,
        max_value=MAX_ALLOWED_DATE,
    )
    submitted = st.form_submit_button("Calculer")

if not submitted:
    st.info("Renseignez une commune, un departement et une periode pour lancer le calcul.")
    st.stop()

if start_date > end_date:
    st.error("La date de debut doit etre anterieure ou egale a la date de fin.")
    st.stop()

if start_date < MIN_ALLOWED_DATE or end_date > MAX_ALLOWED_DATE:
    st.error("Les donnees doivent rester entre 2013-01-01 et 2024-12-31.")
    st.stop()

try:
    commune = communes[commune_index]

    with st.spinner("Telechargement des donnees publiques Meteo-France du departement..."):
        client = PublicMeteoFranceClient()
        stations = client.list_daily_stations(commune.department, start_date, end_date)

    with st.spinner("Recherche de la station valide la plus proche..."):
        selected = select_first_valid_station(
            stations=stations,
            client=client,
            commune_latitude=commune.latitude,
            commune_longitude=commune.longitude,
            start=start_date,
            end=end_date,
        )

    stats = compute_statistics(selected.prepared.data)

except Exception as exc:
    st.error(str(exc))
    st.stop()

st.subheader(f"{commune.name} ({commune.department})")

station_col, distance_col, missing_col = st.columns(3)
station_col.metric("Station utilisee", f"{selected.station_name} ({selected.station_id})")
distance_col.metric("Distance station-commune", f"{selected.distance_km:.1f} km")
missing_col.metric("Donnees manquantes", f"{selected.missing_rate:.1f} %")

total_col, average_col = st.columns(2)
total_col.metric("Nombre total de jours de gel", f"{stats.total_frost_days}")
average_col.metric("Moyenne annuelle", f"{stats.average_frost_days_per_year:.1f} jours/an")

st.subheader("Jours de gel par annee")
fig_year = px.bar(
    stats.yearly,
    x="year",
    y="frost_days",
    labels={"year": "Annee", "frost_days": "Jours de gel"},
)
fig_year.update_xaxes(dtick=1)
st.plotly_chart(fig_year, use_container_width=True)

st.subheader("Probabilite de gel par jour de l'annee")
fig_day = px.line(
    stats.daily,
    x="month_day",
    y="frost_probability_pct",
    labels={
        "month_day": "Jour de l'annee",
        "frost_probability_pct": "Probabilite de gel (%)",
    },
)
fig_day.update_xaxes(type="category", tickangle=45)
st.plotly_chart(fig_day, use_container_width=True)

export = selected.prepared.data.copy()
export["date"] = export["date"].dt.strftime("%Y-%m-%d")
st.download_button(
    "Telecharger les donnees en CSV",
    data=export.to_csv(index=False).encode("utf-8"),
    file_name=f"frost_days_{commune.code}_{start_date}_{end_date}.csv",
    mime="text/csv",
)
st.dataframe(export, use_container_width=True)
