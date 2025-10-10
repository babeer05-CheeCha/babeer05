import streamlit as st
import pandas as pd

st.title("Paper Spec Editor")

# Initialize the DataFrame in session state
if "spec_df" not in st.session_state:
    # Default dataframe
    st.session_state.spec_df = pd.DataFrame({
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
        st.session_state.spec_df = df  # Update session state
        st.success("Spec loaded successfully!")
    except Exception as e:
        st.error(f"Error reading file: {e}")

# Editable dataframe using data_editor
edited_df = st.data_editor(st.session_state.spec_df, num_rows="dynamic")

# Update session state with edited dataframe
st.session_state.spec_df = edited_df

col1, col2 = st.columns(2)
with col1:
    if st.button("Add new row"):
        blank_row = {col: "" for col in st.session_state.spec_df.columns}
        st.session_state.spec_df = pd.concat([st.session_state.spec_df, pd.DataFrame([blank_row])], ignore_index=True)

with col2:
    if st.button("Delete last row"):
        if len(st.session_state.spec_df) > 0:
            st.session_state.spec_df = st.session_state.spec_df[:-1]

# Show updated dataframe again after add/delete actions
st.dataframe(st.session_state.spec_df)

# Provide CSV download button
csv = st.session_state.spec_df.to_csv(index=False).encode("utf-8")
st.download_button(
    label="Download Edited Paper Spec CSV",
    data=csv,
    file_name="paper_spec_edited.csv",
    mime="text/csv",
)
