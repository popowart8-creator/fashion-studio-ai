import copy
import io
import json
import os
import time
import uuid
import zipfile
from pathlib import Path

import requests
import streamlit as st

st.set_page_config(page_title="Fashion Studio AI", layout="wide")
st.title("Fashion Studio AI")
st.caption("Одна модель + одна одежда → три фотографии")
VIEWS = [
    ("front", "Спереди", "Full body front view, facing camera, standing naturally"),
    ("back", "Сзади", "Full body rear view, facing away from camera, back of garment visible"),
    ("free", "Свободная поза", "Full body relaxed editorial fashion pose, three-quarter view"),
]
with st.sidebar:
    st.header("Настройки сервера")
    url = st.text_input("ComfyUI URL", os.getenv("COMFYUI_URL", "http://127.0.0.1:8188")).rstrip("/")
    token = st.text_input("Bearer token", type="password")
    headers = {"Authorization": "Bearer " + token} if token else {}
    wf = st.file_uploader("API workflow примерки", type="json")
    pose_wf = st.file_uploader("API workflow изменения ракурса", type="json")
    garment_id = st.text_input("ID LoadImage одежды", "1")
    person_id = st.text_input("ID LoadImage модели", "2")
    output_id = st.text_input("ID SaveImage примерки", "")
    pose_image_id = st.text_input("ID LoadImage ракурса", "")
    pose_prompt_id = st.text_input("ID текстовой ноды ракурса", "")
    pose_prompt_field = st.text_input("Поле текста ракурса", "text")
    pose_output_id = st.text_input("ID SaveImage ракурса", "")
    timeout = st.number_input("Ожидание задачи, минут", 1, 360, 60)
    if st.button("Проверить соединение"):
        try:
            r = requests.get(url + "/system_stats", headers=headers, timeout=15)
            r.raise_for_status()
            st.success("ComfyUI отвечает")
        except Exception as exc:
            st.error(str(exc))
a, b = st.columns(2)
person = a.file_uploader("Основная модель", type=["jpg","jpeg","png","webp"])
garment = b.file_uploader("Одежда для примерки", type=["jpg","jpeg","png","webp"])
if person:
    a.image(person)
if garment:
    b.image(garment)
st.caption("Вид сзади реконструируется по одной фотографии одежды и может отличаться от реального товара.")

def call(method, path, **kwargs):
    r = requests.request(method, url + path, headers=headers, timeout=60, **kwargs)
    r.raise_for_status()
    return r

def upload(data, suffix, mime):
    name = uuid.uuid4().hex + suffix
    j = call("POST", "/upload/image", files={"image": (name, data, mime)},
             data={"type": "input", "overwrite": "false"}).json()
    return (j["subfolder"] + "/" if j.get("subfolder") else "") + j["name"]

def load_workflow(file, env_name):
    if file:
        return json.loads(file.getvalue())
    path = os.getenv(env_name)
    if path:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    raise ValueError("Не настроен workflow: " + env_name)

def node(graph, node_id, kind=None):
    n = graph[node_id]
    if kind and n["class_type"] != kind:
        raise ValueError(f"Нода {node_id} должна быть {kind}")
    return n["inputs"]

def generate(graph, out):
    pid = call("POST", "/prompt", json={"prompt": graph, "client_id": uuid.uuid4().hex}).json()["prompt_id"]
    deadline = time.monotonic() + timeout * 60
    while time.monotonic() < deadline:
        h = call("GET", "/history/" + pid).json().get(pid)
        if h:
            if h.get("status", {}).get("status_str") == "error":
                raise RuntimeError(str(h["status"]))
            images = h.get("outputs", {}).get(out, {}).get("images", [])
            if not images:
                raise RuntimeError("SaveImage не вернула изображение")
            im = images[0]
            data = call("GET", "/view", params={k: im[k] for k in ("filename","subfolder","type")}).content
            return data, Path(im["filename"]).suffix
        time.sleep(3)
    raise TimeoutError("Истекло время ожидания; проверьте очередь ComfyUI")

if st.button("Сгенерировать 3 фото", type="primary", disabled=not (person and garment)):
    st.session_state["results"] = []
    try:
        base = load_workflow(wf, "TRYON_WORKFLOW")
        pose = load_workflow(pose_wf, "POSE_WORKFLOW")
        if person_id == garment_id:
            raise ValueError("Нужны разные LoadImage")
        node(base, person_id, "LoadImage")
        node(base, garment_id, "LoadImage")
        node(base, output_id, "SaveImage")
        node(pose, pose_image_id, "LoadImage")
        node(pose, pose_output_id, "SaveImage")
        if pose_prompt_field not in node(pose, pose_prompt_id):
            raise ValueError("Не найдено поле текста ракурса")
        graph = copy.deepcopy(base)
        node(graph, person_id)["image"] = upload(person.getvalue(), Path(person.name).suffix, person.type)
        node(graph, garment_id)["image"] = upload(garment.getvalue(), Path(garment.name).suffix, garment.type)
        progress = st.progress(0)
        with st.spinner("Виртуальная примерка..."):
            front, ext = generate(graph, output_id)
        st.session_state["results"].append(("front"+ext, front, VIEWS[0][1]))
        progress.progress(1/3)
        reference = upload(front, ext, "image/jpeg" if ext.lower() in (".jpg",".jpeg") else "image/png")
        for i, (key, label, prompt) in enumerate(VIEWS[1:], 2):
            graph = copy.deepcopy(pose)
            node(graph, pose_image_id)["image"] = reference
            node(graph, pose_prompt_id)[pose_prompt_field] = prompt + ". Preserve the same person, garment design and colors, realistic proportions, neutral gray studio background."
            with st.spinner(label):
                data, ext = generate(graph, pose_output_id)
            st.session_state["results"].append((key+ext, data, label))
            progress.progress(i/3)
    except Exception as exc:
        st.error(str(exc))
results = st.session_state.get("results", [])
if results:
    cols = st.columns(3)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as archive:
        for i, (name, data, label) in enumerate(results):
            cols[i].image(data, caption=label)
            archive.writestr(name, data)
    st.download_button("Скачать фотографии ZIP", buf.getvalue(), "fashion_photos.zip")
