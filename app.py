"""Quant Lab entrypoint — navigation only. Page content lives under pages/."""

from __future__ import annotations

import streamlit as st

st.set_page_config(
    page_title="Quant Lab",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

with st.sidebar:
    st.markdown(
        """
        <div style="padding:0.4rem 0.2rem 1rem 0.2rem;">
          <div style="font-family:'Instrument Serif',Georgia,serif;font-size:1.65rem;letter-spacing:-0.02em;color:#F4F6F8;">
            Quant Lab
          </div>
          <div style="font-size:0.72rem;letter-spacing:0.12em;text-transform:uppercase;color:#8FB5B2;margin-top:0.25rem;">
            Research workshop
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

pages = [
    st.Page("pages/1_Home.py", title="Home", default=True),
    st.Page("pages/2_Look_at_Market.py", title="Look at Market"),
    st.Page("pages/3_Test_a_Rule.py", title="Test a Rule"),
    st.Page("pages/4_Todays_Proposal.py", title="Today's Proposal"),
    st.Page("pages/5_Paper_Practice.py", title="Paper Practice"),
]

st.navigation(pages).run()
