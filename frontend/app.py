import os
import pandas as pd
import streamlit as st
import altair as alt
from supabase import create_client

st.set_page_config(page_title="Hotel & Flight prices", layout="wide")


# -------------------------------
# Supabase connection
# -------------------------------
@st.cache_resource
def get_supabase():
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SERVICE_KEY"]  # backend only
    return create_client(url, key)


# -------------------------------
# Load hotel records
# -------------------------------
@st.cache_data(ttl=60)
def load_last_rooms(limit: int = 1000) -> pd.DataFrame:
    supabase = get_supabase()

    res = (
        supabase.table("room_prices")
        .select("id,scraped_at,room_type,breakfast_included,price,currency")
        .order("scraped_at", desc=True)
        .limit(limit)
        .execute()
    )

    df = pd.DataFrame(res.data or [])
    if df.empty:
        return df

    df["scraped_at"] = pd.to_datetime(df["scraped_at"], utc=True, errors="coerce")
    df["price"] = pd.to_numeric(df["price"], errors="coerce")
    df = df.dropna(subset=["scraped_at", "price"])

    df["scraped_at_local"] = df["scraped_at"].dt.tz_convert("Europe/Warsaw")

    return df.sort_values("scraped_at_local")


# -------------------------------
# Load flight records
# -------------------------------
@st.cache_data(ttl=60)
def load_last_flights(limit: int = 1000) -> pd.DataFrame:
    supabase = get_supabase()

    res = (
        supabase.table("flight_prices")
        .select("id,scraped_at,flight_type,price_pln,airport_from,airport_to,departure_datetime")
        .order("scraped_at", desc=True)
        .limit(limit)
        .execute()
    )

    df = pd.DataFrame(res.data or [])
    if df.empty:
        return df

    df["scraped_at"] = pd.to_datetime(df["scraped_at"], utc=True, errors="coerce")
    df["departure_datetime"] = pd.to_datetime(df["departure_datetime"], utc=True, errors="coerce")
    df["price_pln"] = pd.to_numeric(df["price_pln"], errors="coerce")

    df = df.dropna(subset=["scraped_at", "departure_datetime", "price_pln"])

    df["scraped_at_local"] = df["scraped_at"]
    df["departure_datetime_local"] = df["departure_datetime"]

    return df.sort_values("scraped_at_local")


# -------------------------------
# Sidebar - common settings
# -------------------------------
with st.sidebar:
    st.header("Ustawienia")

    page = st.radio(
        "Wybierz ekran",
        ["Room prices", "Flight prices"]
    )

    limit = st.selectbox(
        "Liczba rekordów",
        options=[100, 500, 1000, 2000],
        index=2
    )


# =========================================================
# SCREEN 1: ROOM PRICES
# =========================================================
if page == "Room prices":
    st.title("📈 Room prices over time")

    df = load_last_rooms(limit=limit)

    if df.empty:
        st.warning("Brak danych w tabeli room_prices.")
        st.stop()

    # -------------------------------
    # Sidebar filters
    # -------------------------------
    with st.sidebar:
        st.header("Filtry pokoi")

        room_types = sorted(df["room_type"].dropna().unique().tolist())
        currencies = sorted(df["currency"].dropna().unique().tolist())

        selected_room_types = st.multiselect(
            "room_type",
            options=room_types,
            default=room_types if room_types else []
        )

        breakfast_choice = st.selectbox(
            "breakfast_included",
            ["both", "true", "false"],
            index=0
        )

        selected_currencies = st.multiselect(
            "currency",
            options=currencies,
            default=currencies[:1] if currencies else []
        )

        min_dt = df["scraped_at_local"].min()
        max_dt = df["scraped_at_local"].max()

        if min_dt == max_dt:
            st.info(f"Tylko jeden punkt czasowy: {min_dt}")
            start_dt = min_dt.to_pydatetime()
            end_dt = max_dt.to_pydatetime()
        else:
            start_dt, end_dt = st.slider(
                "Zakres czasu (Europe/Warsaw)",
                min_value=min_dt.to_pydatetime(),
                max_value=max_dt.to_pydatetime(),
                value=(min_dt.to_pydatetime(), max_dt.to_pydatetime()),
            )

    # -------------------------------
    # Apply filters
    # -------------------------------
    f = df.copy()

    if selected_room_types:
        f = f[f["room_type"].isin(selected_room_types)]

    if selected_currencies:
        f = f[f["currency"].isin(selected_currencies)]

    if breakfast_choice == "true":
        f = f[f["breakfast_included"] == True]
    elif breakfast_choice == "false":
        f = f[f["breakfast_included"] == False]

    f = f[
        (f["scraped_at_local"] >= start_dt) &
        (f["scraped_at_local"] <= end_dt)
    ]

    st.subheader("Wykres ceny w czasie")

    if f.empty:
        st.info("Brak danych dla wybranych filtrów.")
        st.stop()

    f = f.copy()
    f["series"] = (
        f["room_type"].astype(str)
        + " | breakfast=" + f["breakfast_included"].astype(str)
        + " | " + f["currency"].astype(str)
    )

    chart = (
        alt.Chart(f)
        .mark_line(point=True)
        .encode(
            x=alt.X("scraped_at_local:T", title="Time (Europe/Warsaw)"),
            y=alt.Y("price:Q", title="Price"),
            color=alt.Color("series:N", title="Series"),
            tooltip=[
                alt.Tooltip("scraped_at_local:T", title="Time"),
                alt.Tooltip("room_type:N", title="Room"),
                alt.Tooltip("breakfast_included:N", title="Breakfast"),
                alt.Tooltip("currency:N", title="Currency"),
                alt.Tooltip("price:Q", title="Price"),
            ],
        )
        .properties(height=500)
        .interactive()
    )

    st.altair_chart(chart, use_container_width=True)

    st.subheader("Dane (po filtrach)")
    st.dataframe(
        f[["scraped_at_local", "room_type", "breakfast_included", "price", "currency"]]
        .sort_values("scraped_at_local", ascending=False),
        use_container_width=True
    )

    st.subheader("Średnia cena dla typów pokoi (ze śniadaniem / bez śniadania)")

    avg_prices = (
        f.groupby(["room_type", "breakfast_included", "currency"], dropna=False)["price"]
        .mean()
        .reset_index()
        .rename(columns={"price": "avg_price"})
        .sort_values(["room_type", "breakfast_included", "currency"])
    )

    avg_prices["avg_price"] = avg_prices["avg_price"].round(2)
    st.dataframe(avg_prices, use_container_width=True)


# =========================================================
# SCREEN 2: FLIGHT PRICES
# =========================================================
elif page == "Flight prices":
    st.title("✈️ Flight prices over time")

    df = load_last_flights(limit=limit)

    if df.empty:
        st.warning("Brak danych w tabeli flight_prices.")
        st.stop()

    # -------------------------------
    # Sidebar filters
    # -------------------------------
    with st.sidebar:
        st.header("Filtry lotów")

        flight_types = sorted(df["flight_type"].dropna().unique().tolist())
        airports_from = sorted(df["airport_from"].dropna().unique().tolist())
        airports_to = sorted(df["airport_to"].dropna().unique().tolist())

        selected_flight_types = st.multiselect(
            "flight_type",
            options=flight_types,
            default=flight_types if flight_types else []
        )

        selected_airports_from = st.multiselect(
            "airport_from",
            options=airports_from,
            default=airports_from if airports_from else []
        )

        selected_airports_to = st.multiselect(
            "airport_to",
            options=airports_to,
            default=airports_to if airports_to else []
        )

        min_dt = df["scraped_at_local"].min()
        max_dt = df["scraped_at_local"].max()

        if min_dt == max_dt:
            st.info(f"Tylko jeden punkt czasowy: {min_dt}")
            start_dt = min_dt.to_pydatetime()
            end_dt = max_dt.to_pydatetime()
        else:
            start_dt, end_dt = st.slider(
                "Zakres czasu scrape (Europe/Warsaw)",
                min_value=min_dt.to_pydatetime(),
                max_value=max_dt.to_pydatetime(),
                value=(min_dt.to_pydatetime(), max_dt.to_pydatetime()),
            )

    # -------------------------------
    # Apply filters
    # -------------------------------
    f = df.copy()

    if selected_flight_types:
        f = f[f["flight_type"].isin(selected_flight_types)]

    if selected_airports_from:
        f = f[f["airport_from"].isin(selected_airports_from)]

    if selected_airports_to:
        f = f[f["airport_to"].isin(selected_airports_to)]

    f = f[
        (f["scraped_at_local"] >= start_dt) &
        (f["scraped_at_local"] <= end_dt)
    ]

    st.subheader("Wykres ceny lotów w czasie")

    if f.empty:
        st.info("Brak danych dla wybranych filtrów.")
        st.stop()

    f = f.copy()
    f["route"] = f["airport_from"].astype(str) + " → " + f["airport_to"].astype(str)
    f["series"] = f["flight_type"].astype(str) + " | " + f["route"].astype(str)

    # wyciągnięcie samej daty bez godziny
    f["scraped_day"] = pd.to_datetime(f["scraped_at_local"]).dt.floor("D")

    # średnia cena dla tego samego dnia i tej samej trasy/typu lotu
    f_avg = (
        f.groupby(
            ["scraped_day", "flight_type", "airport_from", "airport_to", "route", "series"],
            as_index=False
        )["price_pln"]
        .mean()
    )

    chart = (
        alt.Chart(f_avg)
        .mark_line(point=True)
        .encode(
            x=alt.X("scraped_day:T", title="Scraped day (Europe/Warsaw)"),
            y=alt.Y("price_pln:Q", title="Average price [PLN]"),
            color=alt.Color("series:N", title="Series"),
            tooltip=[
                alt.Tooltip("scraped_day:T", title="Day"),
                alt.Tooltip("flight_type:N", title="Flight type"),
                alt.Tooltip("airport_from:N", title="From"),
                alt.Tooltip("airport_to:N", title="To"),
                alt.Tooltip("price_pln:Q", title="Average price [PLN]", format=".2f"),
            ],
        )
        .properties(height=500)
        .interactive()
    )

    st.altair_chart(chart, use_container_width=True)

    st.subheader("Dane (po filtrach)")
    st.dataframe(
        f[[
            "scraped_at_local",
            "flight_type",
            "airport_from",
            "airport_to",
            "departure_datetime_local",
            "price_pln"
        ]].sort_values("scraped_at_local", ascending=False),
        use_container_width=True
    )

    st.subheader("Średnia cena lotów")

    avg_flights = (
        f.groupby(
            ["flight_type", "airport_from", "airport_to"],
            dropna=False
        )["price_pln"]
        .mean()
        .reset_index()
        .rename(columns={"price_pln": "avg_price_pln"})
        .sort_values(["flight_type", "airport_from", "airport_to"])
    )

    avg_flights["avg_price_pln"] = avg_flights["avg_price_pln"].round(2)
    st.dataframe(avg_flights, use_container_width=True)