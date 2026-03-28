import streamlit as st
import pandas as pd
from datetime import timedelta
from io import BytesIO

st.set_page_config(page_title="NSE Futures vs Cash")

st.title("📊 NSE Futures vs Cash Downloader")

# -------- SAFE IMPORT -------- #
try:
    from nselib import capital_market, derivatives
    NSE_AVAILABLE = True
except Exception as e:
    NSE_AVAILABLE = False
    st.error(f"nselib not working on cloud ❌: {e}")


# -------- FETCH FUNCTION -------- #
def fetch_data(start_date, end_date):
    if not NSE_AVAILABLE:
        return pd.DataFrame()

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

            # Futures only
            df_fut = df_fo[df_fo['FinInstrmTp'] == 'STF'].copy()
            if df_fut.empty:
                continue

            df_fut['XpryDt'] = pd.to_datetime(df_fut['XpryDt'], errors='coerce')
            df_fut = df_fut.sort_values('XpryDt')

            # Near month futures
            df_near = df_fut.groupby('TckrSymb').first().reset_index()
            df_near = df_near[['TckrSymb', 'OpnPric']]
            df_near.columns = ['Symbol', 'Futures Price']

            # Cash
            df_cash = df_cash[['TckrSymb', 'OpnPric']]
            df_cash.columns = ['Symbol', 'Cash Price']

            # Merge
            merged = pd.merge(df_near, df_cash, on='Symbol')

            # Calculations
            merged['Difference'] = merged['Futures Price'] - merged['Cash Price']
            merged['Percentage (%)'] = (merged['Difference'] / merged['Cash Price']) * 100

            merged['Date'] = dt

            final_data.append(merged)

        except Exception as e:
            st.warning(f"Skipped {dt}: {e}")
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
    with st.spinner("Fetching NSE data..."):
        df = fetch_data(start_date, end_date)

    if not NSE_AVAILABLE:
        st.error("⚠️ nselib not supported on Streamlit Cloud. Run locally for real data.")
    elif df.empty:
        st.error("No data found")
    else:
        st.success("File ready!")

        st.dataframe(df.head())

        excel_data = to_excel(df)

        st.download_button(
            "⬇️ Download Excel",
            data=excel_data,
            file_name=f"nse_futures_{start_date}_{end_date}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )