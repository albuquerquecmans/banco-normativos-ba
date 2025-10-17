import json, re, unicodedata, sys, glob
from pathlib import Path
from typing import Set

DATA = Path("data")
NORMS = DATA / "norms.json"
PATCH_DIR = DATA / "patches"

def strip_acc(s): return unicodedata.normalize("NFKD", s).encode("ascii","ignore").decode("ascii")
def slugify(s):
    s = strip_acc(str(s or "")).lower()
    s = re.sub(r"[^a-z0-9\-]+","-", s)
    return re.sub(r"-{2,}","-", s).strip("-")

def uniq_slug(base, tipo, numero, ano, taken: Set[str]):
    cand = slugify(base) or "norma"
    if cand not in taken: taken.add(cand); return cand
    tna = "-".join([x for x in [slugify(tipo), slugify(numero), slugify(ano)] if x])
    if tna and tna not in taken: taken.add(tna); return tna
    i=2
    while True:
        c=f"{cand}-{i}"
        if c not in taken: taken.add(c); return c
        i+=1

def main():
    NORMS.parent.mkdir(parents=True, exist_ok=True)
    if NORMS.exists():
        data = json.loads(NORMS.read_text(encoding="utf-8"))
    else:
        data = []

    taken = set(n.get("slug","") for n in data if n.get("slug"))
    patches = sorted(glob.glob(str(PATCH_DIR / "*.json")))
    if not patches:
        print("merge_patches: nenhum patch encontrado.")
        return

    for p in patches:
        rec = json.loads(Path(p).read_text(encoding="utf-8"))
        ident = rec.get("identificacao") or f"{rec.get('tipo','')} {rec.get('numero','')} {rec.get('ano','')}".strip()
        slug = uniq_slug(ident, rec.get("tipo",""), rec.get("numero",""), rec.get("ano",""), taken)
        rec["slug"] = slug
        data.append(rec)
        print(f"merge_patches: + {Path(p).name} -> slug={slug}")

    NORMS.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

if __name__ == "__main__":
    main()
