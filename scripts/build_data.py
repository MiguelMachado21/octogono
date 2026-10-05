"""Gera data.json para o app a partir dos CSVs do UFC Stats.

Fonte: https://github.com/Greco1899/scrape_ufc_stats (coleta diária do ufcstats.com).
Uso: python3 build_data.py            # baixa os CSVs e gera data.json
     python3 build_data.py --local DIR # usa CSVs já baixados em DIR
"""
import subprocess
import csv
import io
import json
import re
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

BASE = "https://raw.githubusercontent.com/Greco1899/scrape_ufc_stats/main/"
FILES = ["ufc_event_details", "ufc_fight_results", "ufc_fight_stats", "ufc_fighter_details", "ufc_fighter_tott"]
OUT = Path(__file__).resolve().parent.parent / "site" / "data.json"
UPCOMING = "http://ufcstats.com/statistics/events/upcoming"


def get_html(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            html = r.read().decode("utf-8", "replace")
    except Exception:
        html = ""
    if not html or "Checking your browser" in html:  # desafio de JS do ufcstats.com: abre no Chromium headless
        html = subprocess.run(["node", str(Path(__file__).with_name("fetch_html.js")), url],
                              capture_output=True, text=True, timeout=120, check=True).stdout
    return html


def strip_tags(s):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s)).strip()


def fetch_upcoming(known_ids):
    """Próximos eventos do ufcstats.com (lista de eventos + card de cada um).
    Precisa de acesso a ufcstats.com; se falhar, devolve None e o app mantém a lista anterior."""
    html = get_html(UPCOMING)
    out = []
    for row in re.findall(r'<tr class="b-statistics__table-row">(.*?)</tr>', html, re.S):
        m = re.search(r'href="(http://ufcstats\.com/event-details/[0-9a-f]+)"[^>]*>(.*?)</a>', row, re.S)
        if not m:
            continue
        date = re.search(r'b-statistics__date">(.*?)</span>', row, re.S)
        tds = re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)
        ev = {"id": url_id(m.group(1)), "name": strip_tags(m.group(2)),
              "date": date_iso(strip_tags(date.group(1)), "%B %d, %Y") if date else None,
              "loc": strip_tags(tds[-1]) if len(tds) > 1 else "", "fights": []}
        page = get_html(m.group(1))
        for fr in re.findall(r'<tr class="b-fight-details__table-row[^"]*"[^>]*>(.*?)</tr>', page, re.S):
            fs = re.findall(r'href="http://ufcstats\.com/fighter-details/([0-9a-f]+)"[^>]*>(.*?)</a>', fr, re.S)
            if len(fs) < 2:
                continue
            cells = [strip_tags(c) for c in re.findall(r'<td[^>]*>(.*?)</td>', fr, re.S)]
            wcls = next((c for c in cells if re.search(r"weight|Catch", c, re.I)), "")
            ev["fights"].append({"a": [strip_tags(fs[0][1]), fs[0][0] if fs[0][0] in known_ids else None],
                                 "b": [strip_tags(fs[1][1]), fs[1][0] if fs[1][0] in known_ids else None],
                                 "wc": wcls})
        out.append(ev)
    out.sort(key=lambda e: e["date"] or "9999")
    return out


def load(name, local_dir=None):
    if local_dir:
        text = Path(local_dir, name + ".csv").read_text(encoding="utf-8")
    else:
        with urllib.request.urlopen(BASE + name + ".csv", timeout=120) as r:
            text = r.read().decode("utf-8")
    return [{k.strip(): (v or "").strip() for k, v in row.items()} for row in csv.DictReader(io.StringIO(text))]


def url_id(url):
    return url.rstrip("/").rsplit("/", 1)[-1]


def of(s):
    """'29 of 73' -> (29, 73)"""
    m = re.match(r"(\d+)\s+of\s+(\d+)", s or "")
    return (int(m.group(1)), int(m.group(2))) if m else (0, 0)


def mmss(s):
    m = re.match(r"(\d+):(\d+)", s or "")
    return int(m.group(1)) * 60 + int(m.group(2)) if m else 0


def inches(s):
    m = re.match(r"(\d+)'\s*(\d+)", s or "")
    if m:
        return int(m.group(1)) * 12 + int(m.group(2))
    m = re.match(r"([\d.]+)\"", s or "")
    return float(m.group(1)) if m else None


def num(s):
    m = re.match(r"([\d.]+)", s or "")
    return float(m.group(1)) if m else None


def date_iso(s, fmt):
    try:
        return datetime.strptime(s, fmt).date().isoformat()
    except ValueError:
        return None


def fight_seconds(rnd, time, fmt):
    rounds = [int(x) for x in re.findall(r"\d+", fmt.split("(", 1)[1])] if "(" in fmt else []
    rnd = int(rnd) if rnd.isdigit() else 1
    done = sum((rounds[i] if i < len(rounds) else 5) * 60 for i in range(rnd - 1))
    return done + mmss(time)


def method_group(m):
    m = m.lower()
    if "ko" in m:
        return "KO/TKO"
    if "submission" in m:
        return "Finalização"
    if "decision" in m:
        return "Decisão"
    return "Outro"


def main():
    local = sys.argv[2] if len(sys.argv) > 2 and sys.argv[1] == "--local" else None
    events_raw = load("ufc_event_details", local)
    results = load("ufc_fight_results", local)
    stats = load("ufc_fight_stats", local)
    details = load("ufc_fighter_details", local)
    tott = load("ufc_fighter_tott", local)

    # Eventos (mais recente primeiro)
    events, ev_index = [], {}
    for e in events_raw:
        d = date_iso(e["DATE"], "%B %d, %Y")
        ev_index[e["EVENT"]] = len(events)
        events.append({"id": url_id(e["URL"]), "name": e["EVENT"], "date": d, "loc": e["LOCATION"], "fights": []})

    # Lutadores
    fighters, by_name = {}, {}
    nick = {url_id(d["URL"]): d["NICKNAME"] for d in details}
    for t in tott:
        fid = url_id(t["URL"])
        h, r, w = inches(t["HEIGHT"]), inches(t["REACH"]), num(t["WEIGHT"])
        fighters[fid] = {
            "id": fid, "name": t["FIGHTER"], "nick": nick.get(fid, ""),
            "h": round(h * 2.54) if h else None, "r": round(r * 2.54) if r else None,
            "w": round(w * 0.4536, 1) if w else None, "stance": t["STANCE"],
            "dob": date_iso(t["DOB"], "%b %d, %Y"), "fights": [],
        }
        by_name.setdefault(t["FIGHTER"].lower(), []).append(fid)

    # Estatísticas por luta e lutador (soma dos rounds)
    per = {}
    for s in stats:
        if not s["ROUND"].startswith("Round"):
            continue
        key = (s["EVENT"], s["BOUT"], s["FIGHTER"])
        acc = per.setdefault(key, [0] * 16)
        sig, tot, td = of(s["SIG.STR."]), of(s["TOTAL STR."]), of(s["TD"])
        vals = [int(float(s["KD"] or 0)), sig[0], sig[1], tot[0], tot[1], td[0], td[1],
                int(float(s["SUB.ATT"] or 0)), int(float(s["REV."] or 0)), mmss(s["CTRL"]),
                of(s["HEAD"])[0], of(s["BODY"])[0], of(s["LEG"])[0],
                of(s["DISTANCE"])[0], of(s["CLINCH"])[0], of(s["GROUND"])[0]]
        for i, v in enumerate(vals):
            acc[i] += v

    # Lutas
    fights = []
    for r in results:
        ev = ev_index.get(r["EVENT"])
        names = r["BOUT"].split(" vs. ")
        if ev is None or len(names) != 2:
            continue
        a, b = (n.strip() for n in names)
        oa = r["OUTCOME"].split("/")[0]
        res = {"W": 0, "L": 1, "D": 2}.get(oa, 3)
        ids = [(by_name.get(n.lower()) or [None])[0] for n in (a, b)]
        sec = fight_seconds(r["ROUND"], r["TIME"], r["TIME FORMAT"])
        fx = {
            "id": url_id(r["URL"]), "ev": ev, "a": [a, ids[0]], "b": [b, ids[1]], "res": res,
            "wc": r["WEIGHTCLASS"].replace(" Bout", ""), "method": r["METHOD"], "rnd": r["ROUND"],
            "time": r["TIME"], "fmt": r["TIME FORMAT"], "ref": r["REFEREE"], "sec": sec,
            "sa": per.get((r["EVENT"], r["BOUT"], a)), "sb": per.get((r["EVENT"], r["BOUT"], b)),
        }
        fi = len(fights)
        fights.append(fx)
        events[ev]["fights"].append(fi)
        for fid in ids:
            if fid:
                fighters[fid]["fights"].append(fi)

    # Totais de carreira por lutador
    for f in fighters.values():
        c = {"W": 0, "L": 0, "D": 0, "NC": 0, "winBy": {}, "lossBy": {}, "sec": 0, "titleFights": 0,
             "s": [0] * 16, "o": [0] * 16, "statFights": 0}
        for fi in f["fights"]:
            fx = fights[fi]
            me_a = fx["a"][1] == f["id"]
            res = fx["res"] if me_a else {0: 1, 1: 0}.get(fx["res"], fx["res"])
            g = method_group(fx["method"])
            if res == 0:
                c["W"] += 1
                c["winBy"][g] = c["winBy"].get(g, 0) + 1
            elif res == 1:
                c["L"] += 1
                c["lossBy"][g] = c["lossBy"].get(g, 0) + 1
            elif res == 2:
                c["D"] += 1
            else:
                c["NC"] += 1
            if "Title" in fx["wc"]:
                c["titleFights"] += 1
            mine, theirs = (fx["sa"], fx["sb"]) if me_a else (fx["sb"], fx["sa"])
            if mine and theirs:
                c["statFights"] += 1
                c["sec"] += fx["sec"]
                c["s"] = [x + y for x, y in zip(c["s"], mine)]
                c["o"] = [x + y for x, y in zip(c["o"], theirs)]
        f["c"] = c
        # luta mais recente primeiro (eventos já estão do mais novo ao mais antigo)
        f["fights"].sort(key=lambda i: fights[i]["ev"])
        f["last"] = events[fights[f["fights"][0]]["ev"]]["date"] if f["fights"] else None

    # Só lutadores com pelo menos uma luta no UFC
    fl = [f for f in fighters.values() if f["fights"]]
    try:
        upcoming = fetch_upcoming({f["id"] for f in fl})
        print(f"{len(upcoming)} próximos eventos")
    except Exception as e:  # sem acesso ao ufcstats.com: mantém o que já existia
        print("próximos eventos indisponíveis:", e)
        upcoming = json.loads(OUT.read_text(encoding="utf-8")).get("upcoming", []) if OUT.exists() else []
    today = datetime.now().date().isoformat()
    upcoming = [e for e in upcoming if (e["date"] or "9999") >= today]
    data = {"updated": events[0]["date"] if events else None, "events": events, "fights": fights, "fighters": fl,
            "upcoming": upcoming}
    OUT.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    dup = sum(1 for v in by_name.values() if len(v) > 1)
    print(f"{len(events)} eventos, {len(fights)} lutas, {len(fl)} lutadores, {dup} nomes repetidos, "
          f"{OUT.stat().st_size/1e6:.1f} MB -> {OUT}")


if __name__ == "__main__":
    main()
