import streamlit as st

CSS = """
<style>
.block-container { padding-top: 2rem; max-width: 1200px; }

.hero {
    display: flex; justify-content: space-between; align-items: center;
    gap: 1rem; flex-wrap: wrap;
    padding: 1.1rem 1.4rem; margin-bottom: 1rem; border-radius: 18px;
    background: linear-gradient(135deg, #b3261e 0%, #7d1d3f 55%, #1f6f43 100%);
    color: #fff;
}
.hero h1 { margin: 0; padding: 0; font-size: 1.7rem; color: #fff; }
.hero .sub { opacity: .85; font-size: .95rem; }
.hero .count {
    font-weight: 600; background: rgba(255,255,255,.18);
    padding: .4rem .9rem; border-radius: 999px; white-space: nowrap;
}

div[data-testid="stVerticalBlockBorderWrapper"] { border-radius: 14px; }
/* Pictures keep their natural proportions, centred and never cropped: the card grows to fit.
   Very tall photos are capped so one gift can't take over the page. */
/* Streamlit shrink-wraps the picture's wrappers to its width inside a block frame, so the frame
   itself has to do the centring. */
[data-testid="stFullScreenFrame"]:has([data-testid="stImage"]) { display: flex; justify-content: center; }
[data-testid="stImage"] img {
    border-radius: 10px;
    width: auto !important;
    max-width: 100% !important;
    height: auto !important;
    max-height: 340px !important;
    object-fit: contain !important;
}
.gift-title { font-weight: 650; font-size: 1.05rem; line-height: 1.3; margin: .1rem 0 .15rem; }
.newtag {
    background: #c0392b; color: #fff; border-radius: 999px;
    padding: .05rem .5rem; font-size: .72rem; font-weight: 700; margin-right: .35rem;
}
.muted { opacity: .65; font-size: .85rem; }
</style>
"""


def inject() -> None:
    st.markdown(CSS, unsafe_allow_html=True)
