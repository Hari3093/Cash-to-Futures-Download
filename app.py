import streamlit as st
import pandas as pd
from datetime import timedelta, datetime
from io import BytesIO

from nselib import capital_market, derivatives

st.set_page_config(page_title="NSE Cash to Futures Spread (All Scrips)")

st.title("📊 NSE Cash to Futures Spread (All Scrips)")

# -------- HELPER FUNCTION -------- #
def is_trading_date(date):
    """Check if date is a weekday (NSE trading day)"""
    return date.weekday() < 5  # Monday=0, Friday=4

# -------- FETCH FUNCTION -------- #
def fetch_data(start_date, end_date):
    dates = [
        (start_date + timedelta(days=i)).strftime("%d-%m-%Y")
        for i in range((end_date - start_date).days + 1)
    ]

    final_data = []

    # ✅ Clean UI elements
    status = st.empty()
    progress = st.progress(0)
    total = len(dates)

    for i, dt in enumerate(dates):
        status.info(f"Processing: {dt}")
        progress.progress((i + 1) / total)

        try:
            # -------- CASH DATA -------- #
            cash = capital_market.bhav_copy_equities(dt)
            df_cash = pd.DataFrame(cash)

            if df_cash.empty:
                continue

            # -------- FUTURES DATA -------- #
            fo = derivatives.fno_bhav_copy(dt)
            df_fo = pd.DataFrame(fo)

            if df_fo.empty or 'FinInstrmTp' not in df_fo.columns:
                continue

            # ✅ IMPORTANT FIX (ALL FUTURES)
            df_fut = df_fo[df_fo['FinInstrmTp'].isin(['FUTSTK', 'STF'])].copy()

            if df_fut.empty:
                continue

            # -------- NEAR MONTH -------- #
            df_fut['XpryDt'] = pd.to_datetime(df_fut['XpryDt'], errors='coerce')

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
                continue

            # -------- CALCULATIONS -------- #
            merged['Futures Price'] = pd.to_numeric(merged['Futures Price'], errors='coerce')
            merged['Cash Price'] = pd.to_numeric(merged['Cash Price'], errors='coerce')

            merged['Difference'] = merged['Futures Price'] - merged['Cash Price']
            merged['Percentage (%)'] = (merged['Difference'] / merged['Cash Price']) * 100

            merged['Date'] = dt

            final_data.append(merged)

        except Exception as e:
            status.error(f"{dt} failed: {str(e)}")
            st.write(f"Error on {dt}: {e}")
            continue

    status.success("✅ Completed all dates")

    if final_data:
        df = pd.concat(final_data, ignore_index=True)
        df = df[['Date', 'Symbol', 'Futures Price', 'Cash Price', 'Difference', 'Percentage (%)']]
        
        # Round percentage to 2 decimal places
        df['Percentage (%)'] = df['Percentage (%)'].round(2)
        
        return df

    return pd.DataFrame()


# -------- EXCEL -------- #
def to_excel(df):
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Data')
    buffer.seek(0)
    return buffer.getvalue()


# -------- UI -------- #
start_date = st.date_input("Start Date")
end_date = st.date_input("End Date")

# Validation checks
if start_date > end_date:
    st.error("❌ Start date must be before end date")
    st.stop()

if not is_trading_date(start_date):
    st.warning(f"⚠️ Start date ({start_date}) is not a weekday. NSE is closed on weekends/holidays.")

if not is_trading_date(end_date):
    st.warning(f"⚠️ End date ({end_date}) is not a weekday. NSE is closed on weekends/holidays.")

# Filter to only weekdays
dates = []
for i in range((end_date - start_date).days + 1):
    date = start_date + timedelta(days=i)
    if is_trading_date(date):
        dates.append(date)

if not dates:
    st.error("❌ No trading dates found in the selected range!")
    st.stop()

if st.button("Generate File"):
    with st.spinner("Fetching Cash to Futures Spread data..."):
        df = fetch_data(start_date, end_date)

    if df.empty:
        st.error("❌ No data found. Please try:")
        st.write("• Select dates when NSE is open (Mon-Fri)")
        st.write("• Avoid holidays and market closure dates")
        st.write("• Use recent dates (within last 1-2 months)")
    else:
        st.success(f"✅ Total Rows: {len(df)}")

        # Format display with % sign
        df_display = df.copy()
        df_display['Percentage (%)'] = df_display['Percentage (%)'].apply(lambda x: f"{x:.2f}%")
        
        st.dataframe(df_display.head(10))

        excel_data = to_excel(df)

        st.download_button(
            "⬇️ Download Excel",
            data=excel_data,
            file_name=f"nse_cash_to_futures_{start_date}_{end_date}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )