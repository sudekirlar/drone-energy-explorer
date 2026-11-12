import streamlit as st

PALETTES = {
 'viridis': ['#440154','#414487','#2A788E','#22A884','#7AD151','#FDE725'],
 'phase': {'Take-off':'#E69F00','Cruise':'#0072B2','Maneuver':'#CC79A7','Landing':'#009E73','Unknown':'#999999'},
 'payload': {'0g':'#DCEAF7','250g':'#8DB8D8','500g':'#3977A8','750g':'#173F5F'},
 'categorical': ['#0072B2','#E69F00','#009E73','#CC79A7','#D55E00','#56B4E9'],
 'diverging': ['#B2182B','#EF8A62','#F7F7F7','#67A9CF','#2166AC']}

def plotly_template():
    return {'layout': {'font': {'family':'Inter, Arial, sans-serif','color':'#243447'},
      'paper_bgcolor':'rgba(0,0,0,0)','plot_bgcolor':'rgba(0,0,0,0)',
      'colorway':PALETTES['categorical'],'hoverlabel':{'bgcolor':'#142B3B','font':{'color':'#FFFFFF'}},
      'margin':{'l':45,'r':24,'t':55,'b':45},'legend':{'orientation':'h','y':1.08,'x':0},
      'xaxis':{'gridcolor':'#E8EEF3'},'yaxis':{'gridcolor':'#E8EEF3'}}}

def apply_theme():
    st.markdown('''<style>.block-container{padding-top:1.6rem;max-width:1500px} h1,h2,h3{color:#142B3B;letter-spacing:-.02em} [data-testid="stMetric"]{background:#F3F7FA;border:1px solid #E1EAF0;padding:.8rem 1rem;border-radius:.8rem}</style>''', unsafe_allow_html=True)
