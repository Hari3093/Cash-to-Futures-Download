import streamlit as st
import pandas as pd
from datetime import timedelta, datetime
from io import BytesIO

from nselib import capital_market, derivatives
import time as time_module

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

            df_near = df_near[['TckrSymb', 'ClsPric']].copy()
            df_near.columns = ['Symbol', 'Futures Price']

            # -------- CASH -------- #
            df_cash = df_cash[['TckrSymb', 'ClsPric']].copy()
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
def fetch_today_320pm_data():
    """Fetch today's price difference at 3:20 PM"""
    today = datetime.now().strftime("%d-%m-%Y")
    
    current_hour = datetime.now().hour
    current_minute = datetime.now().minute
    
    # Check if it's after 3:20 PM or allow fetch anytime
    try:
        # -------- CASH DATA -------- #
        cash = capital_market.bhav_copy_equities(today)
        df_cash = pd.DataFrame(cash)
        
        if df_cash.empty:
            return None
        
        # -------- FUTURES DATA -------- #
        fo = derivatives.fno_bhav_copy(today)
        df_fo = pd.DataFrame(fo)
        
        if df_fo.empty or 'FinInstrmTp' not in df_fo.columns:
            return None
        
        # ✅ GET ALL FUTURES
        df_fut = df_fo[df_fo['FinInstrmTp'].isin(['FUTSTK', 'STF'])].copy()
        
        if df_fut.empty:
            return None
        
        # -------- NEAR MONTH -------- #
        df_fut['XpryDt'] = pd.to_datetime(df_fut['XpryDt'], errors='coerce')
        df_fut = df_fut.sort_values(['TckrSymb', 'XpryDt'])
        df_near = df_fut.groupby('TckrSymb').first().reset_index()
        
        df_near = df_near[['TckrSymb', 'ClsPric']].copy()
        df_near.columns = ['Symbol', 'Futures Price']
        
        # -------- CASH -------- #
        df_cash = df_cash[['TckrSymb', 'ClsPric']].copy()
        df_cash.columns = ['Symbol', 'Cash Price']
        
        # -------- MERGE -------- #
        merged = pd.merge(df_near, df_cash, on='Symbol', how='inner')
        
        if merged.empty:
            return None
        
        # -------- CALCULATIONS -------- #
        merged['Futures Price'] = pd.to_numeric(merged['Futures Price'], errors='coerce')
        merged['Cash Price'] = pd.to_numeric(merged['Cash Price'], errors='coerce')
        merged['Difference'] = merged['Futures Price'] - merged['Cash Price']
        merged['Percentage (%)'] = (merged['Difference'] / merged['Cash Price']) * 100
        merged['Fetch Time'] = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        
        return merged[['Symbol', 'Futures Price', 'Cash Price', 'Difference', 'Percentage (%)', 'Fetch Time']]
        
    except Exception as e:
        return None

def to_excel(df):
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Data')
    buffer.seek(0)
    return buffer.getvalue()


# -------- UI TABS -------- #
tab1, tab2 = st.tabs(["📅 Historical Data", "⏰ Today @ 3:20 PM"])

with tab2:
    st.subheader("Today's Price Difference at 3:20 PM")
    st.write(f"*Current Time: {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}*")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        st.info("📌 NSE Market Hours: 09:15 AM - 03:30 PM")
    
    with col2:
        if st.button("🔄 Fetch Now", key="fetch_320pm"):
            with st.spinner("Fetching today's 3:20 PM data..."):
                today_data = fetch_today_320pm_data()
            
            if today_data is None:
                st.error("❌ No data available. Market may be closed or no data published yet.")
            elif today_data.empty:
                st.warning("⚠️ No matching scrips found today.")
            else:
                st.success(f"✅ Fetched {len(today_data)} scrips")
                
                # Format for display
                df_display = today_data.copy()
                df_display['Difference'] = df_display['Difference'].round(2)
                df_display['Percentage (%)'] = df_display['Percentage (%)'].apply(lambda x: f"{x:.2f}%")
                df_display['Futures Price'] = df_display['Futures Price'].round(2)
                df_display['Cash Price'] = df_display['Cash Price'].round(2)
                
                # Color code positive/negative differences
                st.dataframe(df_display, use_container_width=True)
                
                # Download option
                excel_data = to_excel(today_data)
                st.download_button(
                    "⬇️ Download Today's Data",
                    data=excel_data,
                    file_name=f"nse_prices_320pm_{datetime.now().strftime('%d-%m-%Y')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

with tab1:
    st.subheader("Historical Price Differences")
    
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
