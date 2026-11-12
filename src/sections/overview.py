import streamlit as st
from src.sections.common import example_card

def render(df, filters):
    st.header('Overview & Data Quality')
    id_col = next((c for c in ('flight','flight_id','Flight','id') if c in df.columns), None)
    a,b,c = st.columns(3)
    a.metric('Filtered flights', f'{df[id_col].nunique():,}' if id_col else f'{len(df):,}')
    b.metric('Rows in view', f'{len(df):,}')
    c.metric('Variables', f'{df.shape[1]:,}')
    st.caption('All sections share the same sidebar FilterState. Filters update this KPI and every chart.')
    example_card(df)
    with st.expander('Current filter state'):
        st.json({'payloads':list(filters.payloads),'altitudes':list(filters.altitudes),'speeds':list(filters.speeds),'hide_flagged':filters.hide_flagged,'include_other_routes':filters.include_other_routes})
