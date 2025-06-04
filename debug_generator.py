import random
import datetime
import sys

from config import PARAMETERS, CIM_EMOTIONS, EMOTION_COEFF
from utils.storage import save_json, save_json_named


def gen(uid: int, days: int = 547, use_date_name: bool = False) -> None:
    start = datetime.date.today() - datetime.timedelta(days=days)
    for i in range(days):
        day = start + datetime.timedelta(days=i)
        record = {"date": day.isoformat(), "summary": ""}
        for key, _ in PARAMETERS:
            if random.random() < 0.1:
                record[key] = None
            else:
                record[key] = random.randint(-3, 3)
        if use_date_name:
            fname = f"mood_{day.strftime('%Y%m%d')}.json"
            save_json_named(uid, "mood", fname, record)
        else:
            save_json(uid, "mood", "mood", record)

        emotions = random.sample(CIM_EMOTIONS, k=random.randint(1, 3))
        intensity = round(random.uniform(0.5, 3.0), 2)
        coeffs = [EMOTION_COEFF.get(e.lower(), 0) for e in emotions]
        cim_score = round(intensity * sum(coeffs) / len(coeffs), 2) if coeffs else None
        metrics = {"intensity": intensity, "emotions": emotions}
        if cim_score is not None:
            metrics["cim_score"] = cim_score

        dream = {"dream": "", "analysis": "", "metrics": metrics, "date": day.isoformat()}
        if use_date_name:
            fname_d = f"dream_{day.strftime('%Y%m%d')}.json"
            save_json_named(uid, "dreams", fname_d, dream)
        else:
            save_json(uid, "dreams", "dream", dream)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python debug_generator.py <user_id>")
        sys.exit(1)
    gen(int(sys.argv[1]))
