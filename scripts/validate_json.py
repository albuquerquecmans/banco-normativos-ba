import argparse, json, sys
from pathlib import Path

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--schema", required=True)
    p.add_argument("--data", required=True)
    args = p.parse_args()

    try:
        import jsonschema
    except ImportError:
        print("Installing jsonschema...", flush=True)
        import subprocess, sys as _sys
        subprocess.check_call([_sys.executable, "-m", "pip", "install", "jsonschema"])
        import jsonschema

    schema = json.loads(Path(args.schema).read_text(encoding="utf-8"))
    data = json.loads(Path(args.data).read_text(encoding="utf-8"))

    # valida
    jsonschema.validate(instance=data, schema=schema)

    # checagens leves
    slugs = set()
    for i, n in enumerate(data, 1):
        slug = (n.get("slug") or "").strip()
        ident = (n.get("identificacao") or "").strip()
        if not slug or not ident:
            print(f"[ERRO] item {i}: slug/identificacao vazio(s)")
            sys.exit(1)
        if slug in slugs:
            print(f"[ERRO] slug duplicado: {slug}")
            sys.exit(1)
        slugs.add(slug)

    print("Schema OK e checagens básicas OK.")

if __name__ == "__main__":
    main()
