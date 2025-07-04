import streamlit as st

st.set_page_config(page_title="صفحه تست Streamlit", page_icon="🌓", layout="centered", initial_sidebar_state="collapsed")

st.markdown(
    """
    <style>
    body, .stApp { background: #181825 !important; color: #e0e0e0 !important; }
    .stApp { display: flex; align-items: center; justify-content: center; min-height: 100vh; }
    .main { display: flex; align-items: center; justify-content: center; min-height: 80vh; }
    </style>
    """,
    unsafe_allow_html=True
)

st.markdown("""
<div style="display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:60vh;">
  <h1 style="color:#38bdf8;font-size:2.5rem;">این یک متن تست است</h1>
  <div style="color:#a3a3b3;font-size:1.2rem;margin-top:1em;">صفحه ساده با تم دارک و استایل الهام گرفته از Streamlit</div>
</div>
""", unsafe_allow_html=True)
