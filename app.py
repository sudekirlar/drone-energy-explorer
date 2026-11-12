import streamlit as st
from src.data.loader import load_project_data
from src.data.filters import FilterState, apply_filters
from src.theme import apply_theme
from src.sections import overview, flight_temporal, energy, multivariate_ml

st.set_page_config(page_title='Drone Delivery Energy Explorer', page_icon='🚁', layout='wide')
apply_theme()
st.title('🚁 Drone Delivery Energy Explorer')
st.caption('Explore how payload, target speed and altitude relate to drone energy use and estimated flight phases.')

@st.cache_data(show_spinner='Loading flight data…')
def get_data():
    return load_project_data()

try:
    data = get_data()
except Exception as exc:
    st.error('Could not load the project data. Check the T0/T1 loader and CSV location.')
    st.exception(exc)
    st.stop()
if getattr(data, 'attrs', {}).get('is_demo'):
    st.warning('⚠️ Demo data in use: no processed file found in data/. Add data/flight_summary.csv (T0/T1 output).')
if data.empty:
    st.warning('The data loader returned no rows.')
    st.stop()

base = FilterState.from_dataframe(data)
with st.sidebar:
    st.header('Global filters')
    payloads = st.multiselect('Payload', base.payload_options, default=base.payload_options)
    altitudes = st.multiselect('Altitude / flight profile', base.altitude_options, default=base.altitude_options)
    speeds = st.multiselect('Target speed', base.speed_options, default=base.speed_options)
    hide_flagged = st.checkbox('Hide flagged flights', False)
    include_other_routes = st.checkbox('Include R2–R7 routes', True)
if not (payloads and altitudes and speeds):
    st.warning('At least one value must be selected in every filter (Payload, Altitude, Target speed).')
    st.stop()
filters = FilterState(tuple(payloads), tuple(altitudes), tuple(speeds), hide_flagged, include_other_routes)
filtered = apply_filters(data, filters)
if filtered.empty:
    st.warning('No flights match the current filters. Relax a filter in the sidebar.')
    st.stop()

sections = {'Overview': overview, 'Flight & Temporal': flight_temporal, 'Energy & Conditions': energy, 'Multivariate & ML': multivariate_ml}
section = st.segmented_control('Dashboard section', list(sections), default='Overview', selection_mode='single') or 'Overview'
st.divider()
sections[section].render(filtered, filters)

with st.sidebar:
    st.divider()
    id_col = next((c for c in ('flight', 'flight_id', 'Flight', 'id') if c in filtered.columns), None)
    st.metric('Filtered flights', f"{filtered[id_col].nunique():,}" if id_col else f'{len(filtered):,}')
    st.caption(f'{len(filtered):,} filtered records')
