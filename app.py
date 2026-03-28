import streamlit as st
import pandas as pd
import requests
from io import BytesIO
from datetime import datetime

st.set_page_config(page_title="NSE Arbitrage Downloader")

st.title("📊 NSE Futures vs Cash Downloader")

# -------- INPUT -------- #
date = st.date_input("Select Date")

# -------- NSE FETCH -------- #
def fetch_nse_data(date):
    try:
        session = requests.Session()

        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept-Language": "en-US,en;q=0.9",
        }

        # Format date
        date_str = date.strftime("%d-%b-%Y").upper()

        # URLs
        cash_url = f"https://www.nseindia.com/api/equity-stockIndices?index=NIFTY%2050"
        fo_url = f"https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY"

        # Initial request (important for cookies)
        session.get("https://www.nseindia.com", headers=headers)

        # Fetch data
        cash_res = session.get(cash_url, headers=headers).json()
        fo_res = session.get(fo_url, headers=headers).json()

        # -------- CASH -------- #
        cash_data = []
        for item in cash_res["data"]:
            cash_data.append({
                "Symbol": item["symbol"],
                "Cash Price": item["lastPrice"]
            })

        df_cash = pd.DataFrame(cash_data)

        # -------- FUTURES (SIMULATED FROM FO) -------- #
        fo_data = []
        for item in fo_res["records"]["data"]:
            if "CE" in item:
                fo_data.append({
                    "Symbol": item["CE"]["underlying"],
                    "Futures Price": item["CE"]["lastPrice"]
                })

        df_fo = pd.DataFrame(fo_data).drop_duplicates()

        # -------- MERGE -------- #
        df = pd.merge(df_cash, df_fo, on="Symbol", how="inner")

        df["Difference"] = df["Futures Price"] - df["Cash Price"]
        df["Percentage (%)"] = (df["Difference"] / df["Cash Price"]) * 100

        df["Date"] = date_str

        df = df[["Date", "Symbol", "Futures Price", "Cash Price", "Difference", "Percentage (%)"]]

        return df

    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return pd.DataFrame()


# -------- EXCEL -------- #
def to_excel(df):
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False)
    return buffer.getvalue()


# -------- BUTTON -------- #
if st.button("Generate & Download"):
    with st.spinner("Fetching NSE data..."):
        df = fetch_nse_data(date)

    if df.empty:
        st.error("No data found")
    else:
        st.success("Data ready!")

        st.dataframe(df.head())

        excel_data = to_excel(df)

        st.download_button(
            label="⬇️ Download Excel",
            data=excel_data,
            file_name=f"nse_futures_{date}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )