import streamlit as st

def render(df, filters):
    st.header('Energy & Experimental Conditions')
    st.write('Integration area for the flight-phase energy Sankey, experiment treemap, and payload × speed × power heatmap.')
    st.metric('Rows available after shared filters', f'{len(df):,}')
    st.info('Use validated energy values and estimated phase labels from the T0/T1 preprocessing output; do not recalculate them here.')
