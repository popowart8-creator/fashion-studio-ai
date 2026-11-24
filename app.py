import os, sys, io
import streamlit as st
from PIL import Image
import torch
from fashn_vton import TryOnPipeline

st.set_page_config(page_title="Fashion Studio AI")
st.title("Fashion Studio AI")
weights = st.sidebar.text_input("Weights directory", os.getenv("FASHN_WEIGHTS", "weights"))
device = st.sidebar.selectbox("Device", ["cpu", "cuda"] if torch.cuda.is_available() else ["cpu"])
steps = st.sidebar.slider("Steps", 5, 50, 30)
category = st.selectbox("Category", ["tops", "bottoms", "one-pieces"])
a,b = st.columns(2)
person = a.file_uploader("Model", type=["jpg","jpeg","png"])
garment = b.file_uploader("Garment", type=["jpg","jpeg","png"])
@st.cache_resource
def pipeline(weights, device):
    return TryOnPipeline(weights_dir=weights, device=device)
if person and garment:
    p = Image.open(person).convert("RGB")
    g = Image.open(garment).convert("RGB")
    a.image(p)
    b.image(g)
    if st.button("Generate"):
        try:
            with st.spinner("Generating..."):
                result = pipeline(weights, device)(person_image=p, garment_image=g, category=category, num_timesteps=steps)
                st.session_state["result"] = result.images[0]
        except Exception as exc:
            st.exception(exc)
if "result" in st.session_state:
    image = st.session_state["result"]
    st.image(image)
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    st.download_button("Download PNG", buf.getvalue(), "tryon.png", "image/png")
