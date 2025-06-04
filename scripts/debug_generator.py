import random
import datetime
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parents[1]
try:
    from config import PARAMETERS
    from utils.storage import save_jsonl
except ModuleNotFoundError:
    if str(BASE_DIR) not in sys.path:
        sys.path.append(str(BASE_DIR))
    from config import PARAMETERS
    from utils.storage import save_jsonl


def gen(uid: int, days: int = 547) -> None:
    start = datetime.date.today() - datetime.timedelta(days=days)
    for i in range(days):
        day = start + datetime.timedelta(days=i)
        record = {"date": day.isoformat(), "summary": ""}
        for key, _ in PARAMETERS:
            if random.random() < 0.1:
                record[key] = None
            else:
                record[key] = random.randint(-3, 3)
        save_jsonl(uid, "mood", "mood", record)

        dream = {"dream": "", "analysis": "", "metrics": {}, "date": day.isoformat()}
        save_jsonl(uid, "dreams", "dream", dream)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python debug_generator.py <user_id>")
        sys.exit(1)
    gen(int(sys.argv[1]))
