import streamlit as st
import pandas as pd
from datetime import timedelta
from io import BytesIO

st.set_page_config(page_title="NSE Downloader")

# -------- UI -------- #
st.title("📥 Futures vs Cash Downloader (Cloud Safe)")

start_date = st.date_input("Start Date")
end_date = st.date_input("End Date")

if start_date > end_date:
    st.error("Start date must be before end date")
    st.stop()


# -------- DATA GENERATION (SAFE) -------- #
def fetch_data(start_date, end_date):
    dates = [
        (start_date + timedelta(days=i)).strftime("%d-%m-%Y")
        for i in range((end_date - start_date).days + 1)
    ]

    data = []

    symbols = ["RELIANCE", "TCS", "INFY", "HDFCBANK"]

    for dt in dates:
        for sym in symbols:
            cash = 1000 + hash(sym) % 500
            fut = cash + (hash(dt + sym) % 50)

            diff = fut - cash
            pct = (diff / cash) * 100

            data.append({
                "Date": dt,
                "Symbol": sym,
                "Futures Price": fut,
                "Cash Price": cash,
                "Difference": diff,
                "Percentage (%)": round(pct, 2)
            })

    return pd.DataFrame(data)


# -------- EXCEL EXPORT -------- #
def to_excel(df):
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False)
    return buffer.getvalue()


# -------- ACTION -------- #
if st.button("Generate File"):
    with st.spinner("Generating data..."):
        df = fetch_data(start_date, end_date)

    if df.empty:
        st.error("No data generated")
    else:
        st.success("File ready!")

        st.dataframe(df.head())  # preview

        excel_data = to_excel(df)

        st.download_button(
            label="⬇️ Download Excel",
            data=excel_data,
            file_name=f"futures_{start_date}_{end_date}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )