from pathlib import Path

import yaml

from .models import CurriculumKB, YearKB


def load_curriculum_kb(path: str | Path) -> CurriculumKB:
    path = Path(path)
    data = {}
    if path.is_dir():
        years = {}
        for f in sorted(path.glob("*.yaml")):
            y = yaml.safe_load(f.read_text())
            years[y["year"]] = y
        data = {"years": years}
    else:
        data = yaml.safe_load(Path(path).read_text())
    return CurriculumKB.parse_obj(data)

def get_year_slice(kb: CurriculumKB, year: str) -> YearKB:
    return kb.years[year]

def resolve_topic(ykb: YearKB, subject_key: str, user_text: str):
    subject_key = subject_key.lower()
    if subject_key not in ykb.subjects:
        return None
    subj = ykb.subjects[subject_key]
    text = user_text.lower()
    best = (None, -1)
    for t in subj.topics:
        keys = (t.title + " " + t.id).lower().replace("-", " ").split()
        score = sum(1 for k in keys if k in text)
        if score > best[1]:
            best = (t, score)
    topic, score = best
    if topic and score > 0:
        return subj, topic, float(score)
    return subj, subj.topics[0], 1.0  # fallback to first topic
