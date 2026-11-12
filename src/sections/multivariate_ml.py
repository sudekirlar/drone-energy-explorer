import streamlit as st

def render(df, filters):
    st.header('Multivariate Analysis & ML')
    st.write('Integration area for Parallel Coordinates + K-means, SPLOM, and phase × payload violin/box plots.')
    st.metric('Rows available after shared filters', f'{len(df):,}')
    st.info('Add multivariate charts and ML outputs here. All charts should consume the same globally filtered `df`.')
