import streamlit as st
import plotly.express as px
from src.theme import plotly_template

@st.fragment
def example_card(df):
    st.subheader('Reusable example chart card')
    st.caption('Template for chart contributors: select a measure and grouping, inspect hover details, then state the finding.')
    numeric = df.select_dtypes(include='number').columns.tolist()
    if not numeric:
        st.info('No numeric columns available for the example card.'); return
    measure = st.selectbox('Numeric measure', numeric, key='example_measure')
    groups = [c for c in ('payload','route','target_speed','speed','altitude') if c in df.columns and c != measure]
    group = st.selectbox('Group by', ['(none)'] + groups, key='example_group')
    fig = px.histogram(df, x=measure, nbins=30) if group == '(none)' else px.box(df, x=group, y=measure, color=group, points='outliers')
    fig.update_layout(**plotly_template()['layout'], height=360)
    st.plotly_chart(fig, use_container_width=True)
    st.info(f'**Finding box — current filtered data:** median {measure} = {df[measure].median():,.3g}. Replace this with a chart-specific interpretation.')
