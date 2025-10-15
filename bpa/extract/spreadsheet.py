from pathlib import Path
import pandas as pd
import json
from slugify import slugify

TIPOS_LEI_DECRETO = {"Lei", "Decreto"}

def _norm_slug(tipo, numero, ano):
    return slugify(f"{tipo}-{numero}-{ano}")

def read_xlsx_to_json(xlsx_path: str, out_json: str):
    df = pd.read_excel(xlsx_path)

    def pick(row, key, default=""):
        # tenta chave com e sem cedilha
        candidates = [key, key.replace("ç","c")]
        for cand in candidates:
            for col in row.index:
                if str(col).strip().lower() == cand:
                    return row[col]
        return default

    records = []
    for _, row in df.iterrows():
        tipo = str(pick(row, "tipo")).strip()
        numero = str(pick(row, "numero")).strip()
        ano = str(pick(row, "ano")).strip()
        slug = _norm_slug(tipo, numero, ano) if tipo and numero and ano else slugify(str(pick(row, "identificacao") or pick(row, "identificação") or ""))

        identificacao = str(pick(row, "identificacao") or pick(row, "identificação")).strip()
        ementa = str(pick(row, "ementa")).strip()
        data = str(pick(row, "data")).strip()
        vigencia = str(pick(row, "vigencia") or pick(row, "vigência")).strip() or "Vigente"
        tema = str(pick(row, "tema")).strip()
        subtemas = str(pick(row, "subtemas") or pick(row, "subtema(s)")).strip()
        link = str(pick(row, "link")).strip()

        fonte_planalto = link if tipo in TIPOS_LEI_DECRETO and link else ""
        fonte_dou = link if tipo not in TIPOS_LEI_DECRETO and link else ""

        records.append({
            "slug": slug,
            "tipo": tipo,
            "numero": numero,
            "ano": ano,
            "data": data,
            "vigencia": vigencia,
            "identificacao": identificacao,
            "ementa": ementa,
            "tema": tema,
            "subtemas": subtemas,
            "fonte_dou": fonte_dou,
            "fonte_planalto": fonte_planalto,
        })

    Path(out_json).parent.mkdir(parents=True, exist_ok=True)
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
