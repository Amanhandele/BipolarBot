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
    ("thought_speed","Скорость мыслей"),
    ("impulsivity","Импульсивность"),
    ("irritability","Раздражительность")
]
def _set_path(uid:int): return BASE_DIR/str(uid)/"settings.json"
def load_user_times(uid:int):
    p=_set_path(uid)
    if p.exists():
        d=json.loads(p.read_text())
        mt=list(map(int,d.get("morning","08:00").split(":")))
        et=list(map(int,d.get("evening","21:00").split(":")))
        return time(*mt), time(*et)
    return DEFAULT_MORNING, DEFAULT_EVENING
def save_user_times(uid:int, m:str, e:str):
    p=_set_path(uid); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"morning":m,"evening":e}))
