import streamlit as st
import pandas as pd
from datetime import timedelta
from io import BytesIO
from nselib import capital_market, derivatives


def fetch_data(start_date, end_date):
    dates = [
        (start_date + timedelta(days=i)).strftime("%d-%m-%Y")
        for i in range((end_date - start_date).days + 1)
    ]

    final_data = []

    for dt in dates:
        try:
            df_cash = pd.DataFrame(capital_market.bhav_copy_equities(dt))
            df_fo = pd.DataFrame(derivatives.fno_bhav_copy(dt))

            if df_cash.empty or df_fo.empty or 'FinInstrmTp' not in df_fo.columns:
                continue

            df_fut = df_fo[df_fo['FinInstrmTp'] == 'STF'].copy()
            if df_fut.empty:
                continue

            df_fut['XpryDt'] = pd.to_datetime(df_fut['XpryDt'], errors='coerce')
            df_fut = df_fut.sort_values('XpryDt')

            df_near = df_fut.groupby('TckrSymb').first().reset_index()
            df_near = df_near[['TckrSymb', 'OpnPric']]
            df_near.columns = ['Symbol', 'Futures Price']

            df_cash = df_cash[['TckrSymb', 'OpnPric']]
            df_cash.columns = ['Symbol', 'Cash Price']

            merged = pd.merge(df_near, df_cash, on='Symbol')

            merged['Difference'] = merged['Futures Price'] - merged['Cash Price']

            # ✅ NEW: Percentage calculation
            merged['Percentage (%)'] = (merged['Difference'] / merged['Cash Price']) * 100

            merged['Date'] = dt

            final_data.append(merged)

        except:
            continue

    if final_data:
        df = pd.concat(final_data, ignore_index=True)

        # ✅ Column order
        df = df[['Date', 'Symbol', 'Futures Price', 'Cash Price', 'Difference', 'Percentage (%)']]

        return df

    return pd.DataFrame()


def to_excel(df):
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False)
    return buffer.getvalue()


# -------- UI -------- #

st.title("📥 NSE Futures vs Cash Downloader")

start_date = st.date_input("Start Date")
end_date = st.date_input("End Date")

if st.button("Generate File"):
    df = fetch_data(start_date, end_date)

    if df.empty:
        st.error("No data found")
    else:
        st.success("File ready!")

        excel_data = to_excel(df)

        st.download_button(
            "⬇️ Download Excel",
            data=excel_data,
            file_name=f"futures_{start_date}_{end_date}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )