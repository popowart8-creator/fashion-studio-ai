# Fashion Studio AI

Local virtual try-on prototype using FASHN VTON 1.5 and Streamlit.

## Setup
Install Python 3.11 and FASHN VTON 1.5 from https://github.com/fashn-AI/fashn-vton-1.5 following its instructions, including PyTorch and model weights. Activate that Python environment, run install.bat, then start.bat. Enter the absolute weights directory in the sidebar. Select CPU or CUDA and upload person and garment photos.

This reconstructed prototype has not been integration-tested. Model weights and personal photos are not included. It generates one image per request; batch generation and API are not implemented. CPU inference can take hours. Check upstream model and dependency licenses before commercial deployment.
