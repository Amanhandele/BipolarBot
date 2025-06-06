import os, json
from datetime import time
from pathlib import Path
BASE_DIR = Path(__file__).with_suffix('').parent / "data"
BASE_DIR.mkdir(exist_ok=True)
DEFAULT_MORNING=time(8,0)
DEFAULT_EVENING=time(21,0)
PARAMETERS=[
    ("mood","Настроение"),
    ("energy","Энергия"),
    ("libido","Либидо"),
    ("thought_speed","Скорость мыслей"),
    ("impulsivity","Импульсивность"),
    ("irritability","Раздражительность"),
]

# Параметры для построения графиков (дополнительно CIM-score)
GRAPH_PARAMS=PARAMETERS+[('cim_score','CIM-score')]

# Список всех эмоций для CIM-анализа
CIM_EMOTIONS=[
    # негативные
    'страх','беспомощность','тревога','угроза','горе','потеря','разочарование',
    'отстранённость','стыд','отвращение','агрессия','ярость','вина','смущение',
    'унижение','зависть','ревность','паника',
    # позитивные
    'утешение','любовь','радость','принятие','сила','уверенность','надежда',
    'свобода','восторг','доверие','игривость','юмор','вдохновение',
    # амбивалентные
    'интерес','удивление','стремление','ожидание','ностальгия',
    'печальное умиротворение','изумление','тоска',
    # нейтральные
    'оцепенение','пустота','отрешённость','тишина','покой'
]

# коэффициенты эмоций для вычисления CIM-score
EMOTION_COEFF={
    'страх':-1.0,
    'горе':-1.0,
    'отвращение':-1.0,
    'вина':-1.0,
    'беспомощность':-1.0,
    'стыд':-0.5,
    'тревога':-0.5,
    'тоска':-0.5,
    'оцепенение':0.0,
    'пустота':0.0,
    'надежда':0.5,
    'утешение':0.5,
    'любовь':1.0,
    'радость':1.0,
    'сила':1.0,
    'вдохновение':1.0,
}
def _set_path(uid:int) -> Path:
    return BASE_DIR/str(uid)/"settings.json"

def _load_settings(uid:int) -> dict:
    p=_set_path(uid)
    if p.exists():
        try:
            return json.loads(p.read_text())
        except Exception:
            return {}
    return {}

def _save_settings(uid:int, data:dict):
    p=_set_path(uid)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False))
def load_user_times(uid:int):
    d=_load_settings(uid)
    mt=list(map(int,d.get("morning","08:00").split(":")))
    et=list(map(int,d.get("evening","21:00").split(":")))
    return time(*mt), time(*et)
def save_user_times(uid:int, m:str, e:str):
    data=_load_settings(uid)
    data["morning"]=m
    data["evening"]=e
    _save_settings(uid,data)

# ─── работа с пользовательскими параметрами ───────────────
def load_custom_params(uid:int):
    d=_load_settings(uid)
    return d.get("custom_params", [])

def add_custom_param(uid:int,label:str)->str:
    d=_load_settings(uid)
    lst=d.setdefault("custom_params", [])
    key=f"custom{len(lst)+1}"
    lst.append({"key":key,"label":label})
    _save_settings(uid,d)
    return key

def user_parameters(uid:int):
    extras=[(p["key"],p["label"]) for p in load_custom_params(uid)]
    return PARAMETERS+extras

def user_graph_params(uid:int):
    return user_parameters(uid)+[("cim_score","CIM-score")]
