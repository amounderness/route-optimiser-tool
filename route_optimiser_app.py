import streamlit as st
import pandas as pd
import numpy as np
from streamlit_sortables import sort_items

# -------------------------
# Helper Functions
# -------------------------
def parse_house_number(address):
    """Extract the first number from an address string."""
    import re
    match = re.search(r'(\d+)', str(address))
    return int(match.group(1)) if match else np.nan

def sort_addresses(df):
    """Sorts each street by odd numbers first, then even numbers."""
    sorted_df = pd.DataFrame()
    for street in df['Street'].unique():
        street_df = df[df['Street'] == street].copy()
        street_df['HouseNum'] = street_df['Address'].apply(parse_house_number)
        odds = street_df[street_df['HouseNum'] % 2 == 1].sort_values('HouseNum')
        evens = street_df[street_df['HouseNum'] % 2 == 0].sort_values('HouseNum')
        combined = pd.concat([odds, evens])
        sorted_df = pd.concat([sorted_df, combined])
    return sorted_df.drop(columns=['HouseNum'])

def assign_route_order(df, ordered_streets):
    df['Street'] = pd.Categorical(df['Street'], categories=ordered_streets, ordered=True)
    df = df.sort_values(['Street'])
    df = sort_addresses(df)
    df = df.reset_index(drop=True)
    df['Route Order'] = df.index + 1
    return df

def assign_canvassers(df, num_canvassers):
    canvasser_ids = [f'Canvasser {i+1}' for i in range(num_canvassers)]
    df['Canvasser'] = [canvasser_ids[i % num_canvassers] for i in range(len(df))]
    return df

# -------------------------
# Streamlit App UI
# -------------------------
st.set_page_config(page_title="Route Optimiser", layout="wide")
st.title("🚚 Route Optimiser Tool (HQ Edition)")

st.markdown("""
Upload your electoral register CSV below. The app will:
1. Detect unique streets
2. Let you define walking order
3. Sort house numbers (odds then evens)
4. Assign route numbers
5. Optionally assign canvassers
6. Export the result to CSV
""")

uploaded_file = st.file_uploader("Upload Electoral Register CSV", type=["csv"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    if 'Street' not in df.columns or 'Address' not in df.columns:
        st.error("CSV must contain at least 'Street' and 'Address' columns.")
    else:
        st.success("File uploaded successfully!")

        streets = sorted(df['Street'].dropna().unique().tolist())

        # Drag-and-drop street ordering
        st.markdown("### 📜 Drag streets to set your walking route:")
        ordered_streets = sort_items(streets, direction="vertical")

        # Optionally assign canvassers
        assign_canv = st.checkbox("Split route among canvassers?")
        if assign_canv:
            num_canvassers = st.number_input("Number of canvassers:", min_value=1, max_value=20, value=4)

        if st.button("🏋️ Generate Route Plan"):
            df_processed = assign_route_order(df.copy(), ordered_streets)

            if assign_canv:
                df_processed = assign_canvassers(df_processed, num_canvassers)

            st.success("Route plan generated!")
            st.dataframe(df_processed.head(20))

            # Export button
            st.download_button(
                label="📂 Download Final CSV",
                data=df_processed.to_csv(index=False).encode('utf-8'),
                file_name="Optimised_Route_Plan.csv",
                mime="text/csv"
            )
