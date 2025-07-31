import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import plotly.express as px
import matplotlib.pyplot as plt  # <-- required for pandas Styler gradient

st.set_page_config(page_title="MAX Network's eCPM Insights", layout="wide")

# ----------- 📥 USER INPUTS -----------
st.title("📊 MAX Network eCPM Insights")

api_key = st.text_input("Enter your AppLovin API Key")
application = st.text_input("Enter your application package (e.g., com.example.app)")

country_scope = st.radio("Do you want data for a specific country?", ['No', 'Yes'])
country = None
if country_scope == 'Yes':
    country = st.text_input("Enter the country code (e.g., us, gb, in)").lower()

ad_format = st.selectbox("Select Ad Format", ["INTER", "REWARD", "BANNER", "MREC"])

start_date = st.date_input("Start Date", datetime.today())
end_date = st.date_input("End Date", datetime.today())

if st.button("Fetch & Analyze"):
    url = "https://r.applovin.com/maxReport"
    params = {
        "api_key": api_key,
        "report_type": "network",
        "start": str(start_date),
        "end": str(end_date),
        "format": "json",
        "columns": "network,application,country,ad_format,ecpm,impressions",
    }

    response = requests.get(url, params=params)
    if response.status_code == 200:
        results = response.json().get("results", [])
        df = pd.DataFrame(results)

        df = df[df['application'] == application]
        if country:
            df = df[df['country'] == country]
        df = df[df['ad_format'] == ad_format]

        df['ecpm'] = pd.to_numeric(df['ecpm'], errors='coerce')
        df['impressions'] = pd.to_numeric(df['impressions'], errors='coerce')

        total_impressions = df['impressions'].sum()
        df['imp_share_numeric'] = (df['impressions'] / total_impressions) * 100
        df = df.sort_values(by="ecpm", ascending=False)
        df['cum_imp_percent'] = df['imp_share_numeric'][::-1].cumsum()[::-1]

        df['imp_share_percent'] = df['imp_share_numeric'].round(0).astype(int).astype(str) + '%'
        df['cum_imp_percent'] = df['cum_imp_percent'].round(0).astype(int).astype(str) + '%'

        st.subheader("📋 Filtered Data")

        # Reorder columns: place imp_share_numeric before imp_share_percent
        cols = list(df.columns)
        if 'imp_share_numeric' in cols and 'imp_share_percent' in cols and 'cum_imp_percent' in cols:
            cols.remove('imp_share_numeric')
            cols.remove('imp_share_percent')
            cols.remove('cum_imp_percent')
            reordered = cols + ['imp_share_numeric', 'imp_share_percent', 'cum_imp_percent']
        else:
            reordered = df.columns

        styled_df = df[reordered].style.background_gradient(
            subset=['imp_share_numeric'], cmap='Greens'
        )
        st.dataframe(styled_df, use_container_width=True)

        st.download_button(
            "📥 Download CSV",
            df[reordered].to_csv(index=False),
            file_name=f"{application.replace('.', '_')}_{country or 'all_countries'}_{ad_format}_{start_date}_to_{end_date}.csv",
            mime='text/csv'
        )

        st.subheader("📈 Impressions by Network")
        df['x_label'] = df['network']
        fig = px.bar(
            df,
            x='x_label',
            y='impressions',
            text='imp_share_percent',
            title="Impressions by Network",
            labels={'x_label': 'Network', 'impressions': 'Impressions'},
            color_discrete_sequence=['green']
        )
        fig.update_traces(
            textposition='outside',
            hovertemplate='Network: %{x}<br>Impressions: %{y:,}<br>Share: %{text}'
        )
        fig.update_layout(
            xaxis_tickangle=-45,
            height=600,
            margin=dict(t=60, b=80)
        )
        st.plotly_chart(fig, use_container_width=True)

    else:
        st.error(f"API Error: {response.status_code} - {response.text}")
