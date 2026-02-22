import os
import pandas as pd
import streamlit as st
import altair as alt
from supabase import create_client

st.set_page_config(page_title="Room prices", layout="wide")


# -------------------------------
# Supabase connection
# -------------------------------
@st.cache_resource
def get_supabase():
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SERVICE_KEY"]  # Secret key (backend only!)
    return create_client(url, key)


# -------------------------------
# Load records with configurable limit
# -------------------------------
@st.cache_data(ttl=60)
def load_last(limit: int = 1000) -> pd.DataFrame:
    supabase = get_supabase()

    res = (
        supabase.table("room_prices")
        .select("id,scraped_at,room_type,breakfast_included,price,currency")
        .order("scraped_at", desc=True)  # najnowsze
        .limit(limit)
        .execute()
    )

    df = pd.DataFrame(res.data or [])
    if df.empty:
        return df

    df["scraped_at"] = pd.to_datetime(df["scraped_at"], utc=True, errors="coerce")
    df["price"] = pd.to_numeric(df["price"], errors="coerce")

    df = df.dropna(subset=["scraped_at", "price"])

    # konwersja na czas lokalny
    df["scraped_at_local"] = df["scraped_at"].dt.tz_convert("Europe/Warsaw")

    # sortowanie chronologiczne do wykresu
    return df.sort_values("scraped_at_local")


# -------------------------------
# UI
# -------------------------------
st.title("📈 Room prices over time")

with st.sidebar:
    st.header("Ustawienia")

    limit = st.selectbox(
        "Liczba rekordów",
        options=[100, 500, 1000, 2000],
        index=2
    )

df = load_last(limit=limit)

if df.empty:
    st.warning("Brak danych w tabeli room_prices.")
    st.stop()

# -------------------------------
# Sidebar filters
# -------------------------------
with st.sidebar:
    st.header("Filtry")

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

# -------------------------------
# Chart
# -------------------------------
st.subheader("Wykres ceny w czasie")

if f.empty:
    st.info("Brak danych dla wybranych filtrów.")
    st.stop()

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

# -------------------------------
# Data table
# -------------------------------
st.subheader("Dane (po filtrach)")

st.dataframe(
    f[["scraped_at_local", "room_type", "breakfast_included", "price", "currency"]]
    .sort_values("scraped_at_local", ascending=False),
    use_container_width=True
)