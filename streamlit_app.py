# streamlit_app.py
import streamlit as st
import pandas as pd
import io
import zipfile

def process_files(uploaded_files):
    all_rows = []

    for uploaded_file in uploaded_files:
        filename = uploaded_file.name
        for line in uploaded_file:
            line = line.decode('latin-1')
            if line.strip():
                fields = [field.strip() for field in line.strip().split('^')]
                fields.insert(0, filename)
                all_rows.append(fields)

    df = pd.DataFrame(all_rows)
    df.columns = ['Filename'] + [f"Column_{i}" for i in range(df.shape[1] - 1)]

    df['Column_8'] = df['Column_8'].replace({'1': 'FAIL', '2': 'PASS', '3': ''})
    df['Column_9'] = df['Column_9'].replace({'0': '', '1': 'F-T', '2': 'P-T', '3': 'P/F-T'})    
    df['Column_19'] = df['Column_19'].replace({'1': 'RV', '0': ''})
    df['Column_21'] = df['Column_21'].replace({'1': 'CP', '0': ''})
    df['Column_22'] = df['Column_22'].replace({'1': 'AR', '0': ''})
    df['Column_23'] = df['Column_23'].replace({'1': 'SKIP', '0': ''})    
    df['Column_24'] = df['Column_24'].replace({'1': 'BVR', '0': ''})
    df['Column_25'] = df['Column_25'].replace({'1': 'VP', '0': ''})
    df['Column_26'] = df['Column_26'].replace({'1': 'INT', '0': ''})

    return df

st.title("MTM File Processor (Web)")

uploaded_files = st.file_uploader("Upload your .mtm files", type="mtm", accept_multiple_files=True)

if uploaded_files:
    df = process_files(uploaded_files)
    st.dataframe(df.head())

    csv = df.to_csv(index=False).encode('latin-1')
    st.download_button("Download CSV", csv, "output.csv", "text/csv")
