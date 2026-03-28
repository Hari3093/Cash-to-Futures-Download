import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="Futures vs Cash Analyzer")

st.title("📊 Futures vs Cash Arbitrage Analyzer")

# -------- FILE UPLOAD -------- #
uploaded_file = st.file_uploader(
    "Upload your NSE Excel file",
    type=["xlsx"]
)

# -------- PROCESS FUNCTION -------- #
def process_data(df):
    # Normalize column names
    df.columns = [col.strip() for col in df.columns]

    required_cols = ["Symbol", "Futures Price", "Cash Price"]

    for col in required_cols:
        if col not in df.columns:
            st.error(f"Missing column: {col}")
            st.stop()

    # Calculate metrics
    df["Difference"] = df["Futures Price"] - df["Cash Price"]
    df["Percentage (%)"] = (df["Difference"] / df["Cash Price"]) * 100

    df["Percentage (%)"] = df["Percentage (%)"].round(2)

    return df


# -------- EXPORT FUNCTION -------- #
def to_excel(df):
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False)
    return buffer.getvalue()


# -------- MAIN LOGIC -------- #
if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file)

        st.success("File uploaded successfully ✅")

        st.subheader("📄 Raw Data Preview")
        st.dataframe(df.head())

        df_processed = process_data(df)

        st.subheader("📊 Processed Data Preview")
        st.dataframe(df_processed.head())

        excel_data = to_excel(df_processed)

        st.download_button(
            label="⬇️ Download Processed Excel",
            data=excel_data,
            file_name="futures_processed.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception as e:
        st.error(f"Error processing file: {e}")