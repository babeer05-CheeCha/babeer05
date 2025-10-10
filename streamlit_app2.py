import streamlit as st
import pandas as pd

st.title("Paper Spec Editor")

# Optional: Load initial template if no file uploaded
default_spec = pd.DataFrame({
    "Product": ["PROD_A", "PROD_B"],
    "Item": ["Item01", "Item02"],
    "Check Type": ["LimitBias", "Limit"],
    "Limit Min": [10, 5],
    "Limit Max": [20, 15],
    "Bias Min": [-2, None],
    "Bias Max": [2, None]
})

uploaded_file = st.file_uploader("Upload Paper Spec CSV", type=["csv"])

if uploaded_file:
    try:
        df = pd.read_csv(uploaded_file)
        st.success("Spec loaded successfully!")
    except Exception as e:
        st.error(f"Error reading file: {e}")
        df = default_spec.copy()
else:
    df = default_spec.copy()
    st.info("No file uploaded. Using default template.")

# Editable dataframe using st.data_editor (Streamlit 1.21+)
edited_df = st.data_editor(df, num_rows="dynamic")

# Buttons for Add and Delete rows
col1, col2 = st.columns(2)

with col1:
    if st.button("Add new row"):
        # Append a blank row
        blank_row = {col: "" for col in edited_df.columns}
        edited_df = pd.concat([edited_df, pd.DataFrame([blank_row])], ignore_index=True)
        st.experimental_rerun()  # Reload to update table (since data_editor is stateless)

with col2:
    if st.button("Delete last row"):
        if len(edited_df) > 0:
            edited_df = edited_df[:-1]
            st.experimental_rerun()

# Save to CSV and provide download button
csv = edited_df.to_csv(index=False).encode("utf-8")
st.download_button(
    label="Download Edited Paper Spec CSV",
    data=csv,
    file_name="paper_spec_edited.csv",
    mime="text/csv",
)
