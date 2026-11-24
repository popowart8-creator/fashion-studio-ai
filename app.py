import streamlit as st
import requests, json, time, uuid, io, zipfile
from pathlib import Path
st.set_page_config(page_title='Fashion Studio AI',layout='wide')
ROOT=Path(__file__).parent
st.title('Fashion Studio AI')
st.caption('Женская модель · Цельная одежда · Серая студия')
poses=['Спереди','Полуоборот','Сбоку','Сзади','В движении','Свободная поза','Детали верха','Детали низа']
with st.sidebar:
    st.header('Подключение ComfyUI')
    url=st.text_input('URL сервера','http://127.0.0.1:8188').rstrip('/')
    token=st.text_input('Bearer token (если нужен)',type='password')
    headers={'Authorization':'Bearer '+token} if token else {}
    if st.button('Проверить соединение'):
        try:
            r=requests.get(url+'/system_stats',headers=headers,timeout=15);r.raise_for_status();r.json();st.success('Сервер отвечает')
        except Exception as e: st.error(str(e))
    wf=st.file_uploader('Workflow ComfyUI (API JSON)',type='json')
    garment_id=st.text_input('ID ноды Load Image — одежда','1')
    person_id=st.text_input('ID ноды Load Image — модель','2')
    output_id=st.text_input('ID ноды Save Image','')
a,b=st.columns(2)
with a:
    front=st.file_uploader('Товар спереди',type=['jpg','jpeg','png','webp'])
    if front: st.image(front,width=220)
with b:
    back=st.file_uploader('Товар сзади',type=['jpg','jpeg','png','webp'])
    if back: st.image(back,width=220)
st.subheader('Библиотека модели')
st.caption('Загрузите фото одной девушки в нужных позах. Для деталей используйте соответствующие референсы. Фон должен быть серым уже на исходных фото.')
refs=[]
for i,p in enumerate(poses):
    refs.append(st.file_uploader(p,type=['jpg','jpeg','png','webp'],key=f'pose{i}'))
def call(method,path,**kw):
    r=requests.request(method,url+path,headers=headers,timeout=60,**kw);r.raise_for_status();return r

def upload(f):
    name=uuid.uuid4().hex+Path(f.name).suffix
    j=call('POST','/upload/image',files={'image':(name,f.getvalue(),f.type)},data={'type':'input','overwrite':'false'}).json()
    return (j.get('subfolder','')+'/' if j.get('subfolder') else '')+j['name']

if st.button('Сгенерировать 8 фото',type='primary'):
    try:
        if not all([front,back,wf,output_id]) or not all(refs): raise ValueError('Нужны оба фото товара, 8 референсов модели, API workflow и ID выходной ноды.')
        base=json.loads(wf.getvalue())
        for n in (garment_id,person_id):
            if base[n]['class_type']!='LoadImage': raise ValueError('ID должен указывать на LoadImage')
        if garment_id==person_id or base[output_id]['class_type']!='SaveImage': raise ValueError('Проверьте ID нод')
        st.session_state['results']=[]
        names=[upload(front),upload(back)]
        progress=st.progress(0)
        for i,ref in enumerate(refs):
            graph=json.loads(json.dumps(base));graph[garment_id]['inputs']['image']=names[int(i==3)];graph[person_id]['inputs']['image']=upload(ref)
            pid=call('POST','/prompt',json={'prompt':graph,'client_id':uuid.uuid4().hex}).json()['prompt_id']
            deadline=time.monotonic()+900
            while time.monotonic()<deadline:
                h=call('GET','/history/'+pid).json().get(pid)
                if h:
                    if h.get('status',{}).get('status_str')=='error': raise RuntimeError('Ошибка workflow: '+str(h['status']))
                    imgs=h.get('outputs',{}).get(output_id,{}).get('images',[])
                    if not imgs: raise RuntimeError('Выходная нода не вернула фото')
                    im=imgs[0];data=call('GET','/view',params={k:im[k] for k in ('filename','subfolder','type')}).content
                    folder=ROOT/'results';folder.mkdir(exist_ok=True);name=f'{uuid.uuid4().hex[:8]}_{i+1:02d}'+Path(im['filename']).suffix
                    (folder/name).write_bytes(data);st.session_state['results'].append((name,data,poses[i]));break
                time.sleep(3)
            else: raise TimeoutError('Сервер не завершил задачу за 15 минут. Проверьте очередь ComfyUI.')
            progress.progress((i+1)/8)
    except Exception as e: st.error(str(e))
results=st.session_state.get('results',[])
if results:
    st.subheader('Результаты — проверьте соответствие товару')
    cols=st.columns(4);buf=io.BytesIO()
    with zipfile.ZipFile(buf,'w') as z:
        for i,(name,data,pose) in enumerate(results):
            cols[i%4].image(data,caption=pose);z.writestr(name,data)
    st.download_button('Скачать ZIP',buf.getvalue(),'fashion_photos.zip')
