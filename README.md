# Fashion Studio AI

Two uploads: person and garment. Three outputs: front try-on, rear view, relaxed pose. Start with Python 3.11 and start.bat or streamlit run app.py.

## Server setup
Requires a working ComfyUI server with two tested API-format workflows: virtual try-on (two LoadImage nodes and SaveImage), and reference-conditioned image editing (LoadImage, editable text prompt, SaveImage). The second must support changing pose and viewpoint while preserving clothing and identity. Supply workflows in sidebar or set TRYON_WORKFLOW and POSE_WORKFLOW to server-side JSON paths. Enter matching node IDs in sidebar. COMFYUI_URL sets default server URL. The app first runs try-on then feeds its output into the two pose edits. No model weights or validated workflows are bundled; choose models compatible with server GPU. Front input should be front-facing. Rear details inferred from a single garment image are not guaranteed accurate. Use authenticated private access; do not expose ComfyUI publicly. Generation has not been integration-tested. README.txt describes the previous eight-reference version.
