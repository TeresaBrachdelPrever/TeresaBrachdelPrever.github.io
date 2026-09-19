#!/usr/bin/env python3
"""Genera index.html e lezioni-aletheia-program.ics a partire da lezioni.json.

Uso: python3 calendario/build.py   (dalla radice del repo, o da qualsiasi cartella)
"""
import json
from datetime import datetime, timedelta, timezone
from html import escape
from pathlib import Path
from urllib.parse import quote
from zoneinfo import ZoneInfo

HERE = Path(__file__).parent
SITE = "teresabrachdelprever.github.io"
ICS_NAME = "lezioni-aletheia-program.ics"
GIORNI = ["lunedì", "martedì", "mercoledì", "giovedì", "venerdì", "sabato", "domenica"]
MESI = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio",
        "agosto", "settembre", "ottobre", "novembre", "dicembre"]

data = json.loads((HERE / "lezioni.json").read_text(encoding="utf-8"))
tz = ZoneInfo(data["timezone"])
durata = timedelta(minutes=data["durata_minuti"])
corso = data["corso"]


def eventi():
    for l in data["lezioni"]:
        inizio = datetime.fromisoformat(l["inizio"]).replace(tzinfo=tz)
        yield {
            **l,
            "inizio_dt": inizio,
            "fine_dt": inizio + durata,
            "titolo_completo": f"{corso} · {l['titolo']}",
            "descrizione": f"{corso}\n{l['titolo']}\n\nEntra su Zoom: {l['zoom']}",
        }


def google_url(e):
    fmt = "%Y%m%dT%H%M%S"
    return (
        "https://calendar.google.com/calendar/render?action=TEMPLATE"
        f"&text={quote(e['titolo_completo'])}"
        f"&dates={e['inizio_dt'].strftime(fmt)}/{e['fine_dt'].strftime(fmt)}"
        f"&ctz={quote(data['timezone'])}"
        f"&details={quote(e['descrizione'])}"
        f"&location={quote(e['zoom'], safe='')}"
    )


def ics_escape(s):
    return s.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def fold(line):
    """Le righe ICS non possono superare 75 byte: si va a capo con uno spazio iniziale."""
    raw = line.encode("utf-8")
    out, first = [], True
    while raw:
        limit = 75 if first else 74
        chunk = raw[:limit]
        while True:  # non spezzare un carattere multibyte
            try:
                chunk.decode("utf-8")
                break
            except UnicodeDecodeError:
                chunk = chunk[:-1]
        out.append(("" if first else " ") + chunk.decode("utf-8"))
        raw = raw[len(chunk):]
        first = False
    return "\r\n".join(out)


def build_ics(evs):
    utc = lambda d: d.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Teresa Brach del Prever//Aletheia Program//IT",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{corso}",
        f"X-WR-TIMEZONE:{data['timezone']}",
        "REFRESH-INTERVAL;VALUE=DURATION:PT12H",
        "X-PUBLISHED-TTL:PT12H",
    ]
    for e in evs:
        lines += [
            "BEGIN:VEVENT",
            f"UID:{e['id']}@{SITE}",
            f"DTSTAMP:{stamp}",
            f"DTSTART:{utc(e['inizio_dt'])}",
            f"DTEND:{utc(e['fine_dt'])}",
            f"SUMMARY:{ics_escape(e['titolo_completo'])}",
            f"DESCRIPTION:{ics_escape(e['descrizione'])}",
            f"LOCATION:{ics_escape(e['zoom'])}",
            f"URL:{e['zoom']}",
            "BEGIN:VALARM",
            "ACTION:DISPLAY",
            f"DESCRIPTION:{ics_escape(e['titolo_completo'])}",
            "TRIGGER:-PT30M",
            "END:VALARM",
            "END:VEVENT",
        ]
    lines.append("END:VCALENDAR")
    return "\r\n".join(fold(l) for l in lines) + "\r\n"


def card(e):
    d = e["inizio_dt"]
    quando = f"{GIORNI[d.weekday()]} {d.day} {MESI[d.month - 1]}"
    orario = f"ore {d.strftime('%H:%M')} – {e['fine_dt'].strftime('%H:%M')}"
    return f"""    <article class="lesson">
      <div class="lesson-date"><span class="day">{d.day}</span><span class="month">{MESI[d.month - 1][:3]}</span></div>
      <div class="lesson-body">
        <h2>{e['emoji']} {escape(e['titolo'])}</h2>
        <p class="when">{quando} · {orario}</p>
        <div class="actions">
          <a class="btn" href="{escape(e.get('calendar_url') or google_url(e))}" target="_blank" rel="noopener">＋ Aggiungi a Google Calendar</a>
          <a class="zoom" href="{escape(e['zoom'])}" target="_blank" rel="noopener">Link Zoom</a>
        </div>
      </div>
    </article>"""


TEMPLATE = (HERE / "template.html").read_text(encoding="utf-8")

evs = list(eventi())
(HERE / ICS_NAME).write_bytes(build_ics(evs).encode("utf-8"))
page = (
    TEMPLATE.replace("{{CORSO}}", escape(corso))
    .replace("{{CARDS}}", "\n".join(card(e) for e in evs))
    .replace("{{SUBSCRIBE_URL}}", f"https://calendar.google.com/calendar/r?cid=webcal://{SITE}/calendario/{ICS_NAME}")
    .replace("{{ICS_NAME}}", ICS_NAME)
)
(HERE / "index.html").write_text(page, encoding="utf-8")
print(f"OK: {len(evs)} lezioni -> index.html, {ICS_NAME}")
