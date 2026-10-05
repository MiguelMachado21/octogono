#!/bin/sh
# Atualiza os dados do site: lutas (CSVs do UFC Stats), próximos eventos e fotos de lutadores novos.
# Uso: sh scripts/atualizar.sh   (roda sozinho todo dia pelo GitHub Actions)
set -e
cd "$(dirname "$0")"
python3 build_data.py
python3 - <<'PY'
import json, re, unicodedata, os
d = json.load(open("../site/data.json"))
res = json.load(open("fotos/res.json")) if os.path.exists("fotos/res.json") else {}
ids = {f["id"] for f in d["fighters"]} | {p[1] for e in d.get("upcoming", []) for x in e["fights"] for p in (x["a"], x["b"]) if p[1]}
names = {f["id"]: f["name"] for f in d["fighters"]}
slug = lambda n: re.sub(r"[^a-z0-9]+", "-", unicodedata.normalize("NFKD", n).encode("ascii", "ignore").decode().lower()).strip("-")
todo = [{"id": i, "name": names[i], "slug": slug(names[i])} for i in ids if i in names and (i not in res or "err" in res[i])]
json.dump(todo, open("fotos/list.json", "w"))
print(len(todo), "lutadores novos para buscar foto")
PY
cd fotos
if [ "$(python3 -c 'import json;print(len(json.load(open("list.json"))))')" != "0" ]; then
  (node crawl.js 4 && python3 proc.py) || echo "fotos: falhou, seguindo sem fotos novas"
fi
rm -f list.json
