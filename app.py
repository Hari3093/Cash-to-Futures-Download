import streamlit as st
import pandas as pd
from datetime import timedelta
from io import BytesIO

from nselib import capital_market, derivatives

st.title("📊 NSE F&O vs Cash (ALL SCRIPS)")

# -------- FETCH FUNCTION -------- #
def fetch_data(start_date, end_date):
    dates = [
        (start_date + timedelta(days=i)).strftime("%d-%m-%Y")
        for i in range((end_date - start_date).days + 1)
    ]

    final_data = []

    for dt in dates:
        st.write(f"Processing {dt}...")

        try:
            # CASH DATA
            cash = capital_market.bhav_copy_equities(dt)
            df_cash = pd.DataFrame(cash)

            if df_cash.empty:
                st.warning(f"No cash data for {dt}")
                continue

            # FUTURES DATA
            fo = derivatives.fno_bhav_copy(dt)
            df_fo = pd.DataFrame(fo)

            if df_fo.empty:
                st.warning(f"No futures data for {dt}")
                continue

            # -------- FIX 1: include FUTSTK -------- #
            if 'FinInstrmTp' not in df_fo.columns:
                st.warning(f"FinInstrmTp missing {dt}")
                continue

            df_fut = df_fo[df_fo['FinInstrmTp'].isin(['FUTSTK', 'STF'])].copy()

            if df_fut.empty:
                st.warning(f"No stock futures {dt}")
                continue

            # -------- FIX 2: expiry parsing -------- #
            df_fut['XpryDt'] = pd.to_datetime(df_fut['XpryDt'], errors='coerce')

            # -------- FIX 3: correct sorting -------- #
            df_fut = df_fut.sort_values(['TckrSymb', 'XpryDt'])

            df_near = df_fut.groupby('TckrSymb').first().reset_index()

            df_near = df_near[['TckrSymb', 'OpnPric']].copy()
            df_near.columns = ['Symbol', 'Futures Price']

            # -------- CASH -------- #
            df_cash = df_cash[['TckrSymb', 'OpnPric']].copy()
            df_cash.columns = ['Symbol', 'Cash Price']

            # -------- MERGE -------- #
            merged = pd.merge(df_near, df_cash, on='Symbol', how='inner')

            if merged.empty:
                st.warning(f"No matching symbols {dt}")
                continue

            # -------- FIX 4: numeric safety -------- #
            merged['Futures Price'] = pd.to_numeric(merged['Futures Price'], errors='coerce')
            merged['Cash Price'] = pd.to_numeric(merged['Cash Price'], errors='coerce')

            merged['Difference'] = merged['Futures Price'] - merged['Cash Price']
            merged['Percentage (%)'] = (merged['Difference'] / merged['Cash Price']) * 100

            merged['Date'] = dt

            final_data.append(merged)

            st.success(f"{dt} → {len(merged)} symbols")

        except Exception as e:
            st.error(f"{dt} failed: {e}")
            continue

    if final_data:
        df = pd.concat(final_data, ignore_index=True)
        df = df[['Date', 'Symbol', 'Futures Price', 'Cash Price', 'Difference', 'Percentage (%)']]
        return df

    return pd.DataFrame()


# -------- EXCEL -------- #
def to_excel(df):
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False)
    return buffer.getvalue()


# -------- UI -------- #
start_date = st.date_input("Start Date")
end_date = st.date_input("End Date")

if start_date > end_date:
    st.error("Start date must be before end date")
    st.stop()

if st.button("Generate File"):
    with st.spinner("Fetching ALL F&O data..."):
        df = fetch_data(start_date, end_date)

    if df.empty:
        st.error("No data found")
    else:
        st.success(f"Total Rows: {len(df)}")

        st.dataframe(df.head())

        excel_data = to_excel(df)

        st.download_button(
            "⬇️ Download Excel",
            data=excel_data,
            file_name=f"nse_fo_full_{start_date}_{end_date}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )