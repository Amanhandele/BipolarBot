import shutil, datetime
from utils.storage import user_dir
def export(uid):
    base=user_dir(uid)
    ts=datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    arch=base.parent/f"export_{uid}_{ts}"
    shutil.make_archive(str(arch),'zip',base)
    return str(arch)+'.zip'
