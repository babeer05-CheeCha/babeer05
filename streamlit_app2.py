import streamlit as st
import pandas as pd
import os

# Folder where paper specs CSVs are stored
PAPER_SPEC_FOLDER = "paper_specs"
MAPPING_FILE = os.path.join(PAPER_SPEC_FOLDER, "mtm_product_map.csv")

# Ensure the folder exists
os.makedirs(PAPER_SPEC_FOLDER, exist_ok=True)

# Create mapping file if not exists
if not os.path.exists(MAPPING_FILE):
    pd.DataFrame(columns=["Filename", "Product"]).to_csv(MAPPING_FILE, index=False)

# Tabs: Paper Spec Editor | MTM-Product Link Editor
tab = st.tabs(["✏️ Paper Spec Editor", "🔗 MTM-Product Link Editor"])

with tab[0]:
    st.header("Paper Spec Editor")

    # List all CSV spec files in the folder
    spec_files = [f for f in os.listdir(PAPER_SPEC_FOLDER) if f.endswith(".csv")]

    selected_spec = st.selectbox("Select a Paper Spec CSV to edit", spec_files + ["<Create New>"])

    if selected_spec == "<Create New>":
        new_name = st.text_input("Enter new paper spec name (without .csv):")
        if new_name:
            new_path = os.path.join(PAPER_SPEC_FOLDER, f"{new_name}.csv")
            if not os.path.exists(new_path):
                df_spec = pd.DataFrame(columns=["Item", "Limit", "Bias", "CompareLimit", "CompareBias"])
                df_spec.to_csv(new_path, index=False)
                st.success(f"Created new paper spec: {new_name}.csv")
                selected_spec = f"{new_name}.csv"
            else:
                st.warning("File already exists.")
    if selected_spec and selected_spec != "<Create New>":
        spec_path = os.path.join(PAPER_SPEC_FOLDER, selected_spec)
        df_spec = pd.read_csv(spec_path)
        edited_spec = st.data_editor(df_spec, num_rows="dynamic", use_container_width=True)

        if st.button("Save Paper Spec"):
            edited_spec.to_csv(spec_path, index=False)
            st.success(f"Saved {selected_spec}")

with tab[1]:
    st.header("MTM-Product Link Editor")

    if os.path.exists(MAPPING_FILE):
        df_map = pd.read_csv(MAPPING_FILE)
    else:
        df_map = pd.DataFrame(columns=["Filename", "Product"])

    edited_map = st.data_editor(df_map, num_rows="dynamic", use_container_width=True)

    if st.button("Save Mapping"):
        edited_map.to_csv(MAPPING_FILE, index=False)
        st.success("Saved MTM to Product mapping")
