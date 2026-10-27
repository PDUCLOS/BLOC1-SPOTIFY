"""Vidéo de présentation (1080p) générée à partir des vraies pages des livrables et du rapport.

Chaîne : scènes HTML -> PNG 1920x1080 (Edge headless) -> narration française
(voix Windows Hortense, System.Speech) -> clips ffmpeg (zoom lent + fondus)
-> concaténation + fond sonore synthétisé (aucun fichier sous licence).
Adapté du générateur du projet LLMRAGlangchain.

Usage (Windows) :  python scripts/promo_video.py
Sortie : docs/video/gouvernance-spotify-promo.mp4 (+ affiche docs/video/poster.png)
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from html import escape
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
IMG = ROOT / "docs" / "img"
OUT = ROOT / "docs" / "video"
WORK = ROOT / "data" / "promo"
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
FFMPEG = shutil.which("ffmpeg") or os.environ.get("FFMPEG", "ffmpeg")
FFPROBE = shutil.which("ffprobe") or str(Path(FFMPEG).with_name("ffprobe.exe"))
FPS = 30
PAD_S = 0.9  # respiration après chaque phrase

CSS = """
:root { --bg:#121614; --ink:#ecf1ee; --muted:#a5b3ab; --accent:#4ade80; --warn:#e3a948; --bad:#f08079; }
* { box-sizing:border-box; margin:0; }
html,body { width:1920px; height:1080px; overflow:hidden; background:var(--bg); color:var(--ink);
  font-family:"IBM Plex Sans",system-ui,sans-serif; }
.stage { width:1920px; height:1080px; padding:110px 140px; display:grid; align-content:center; gap:34px;
  background: radial-gradient(1200px 700px at 85% 15%, #1b3a28 0%, transparent 60%), var(--bg); }
.eyebrow { font:500 26px "IBM Plex Mono",monospace; letter-spacing:.14em; text-transform:uppercase; color:var(--muted); }
h1 { font:700 100px/1.03 "IBM Plex Sans Condensed",sans-serif; letter-spacing:-.015em; max-width:1550px; }
h1 em { font-style:normal; color:var(--accent); }
p.sub { font-size:38px; line-height:1.45; color:var(--muted); max-width:1500px; }
ul { list-style:none; padding:0; display:grid; gap:26px; }
li { font-size:42px; line-height:1.3; padding-left:56px; position:relative; }
li::before { content:""; position:absolute; left:0; top:22px; width:28px; height:4px; background:var(--accent); }
li.bad::before { background:var(--bad); } li.warn::before { background:var(--warn); }
.kpis { display:grid; grid-template-columns:repeat(5,1fr); gap:2px; background:rgba(255,255,255,.14); border-radius:10px; overflow:hidden; }
.kpi { background:var(--bg); padding:40px 30px; display:grid; gap:10px; }
.kpi b { font:700 84px "IBM Plex Sans Condensed",sans-serif; color:#fff; }
.kpi span { font-size:28px; color:var(--muted); line-height:1.3; }
.shotstage { width:1920px; height:1080px; display:grid; grid-template-rows:1fr auto; background:var(--bg); }
.frame { display:grid; place-items:center; padding:48px 60px 26px; overflow:hidden; }
.frame img { max-width:100%; max-height:860px; border-radius:12px; box-shadow:0 30px 80px rgba(0,0,0,.5); border:1px solid rgba(255,255,255,.14); background:#fff; }
.band { padding:26px 60px 40px; display:flex; gap:30px; align-items:baseline; }
.band .tag { font:500 24px "IBM Plex Mono",monospace; color:var(--accent); letter-spacing:.12em; text-transform:uppercase; white-space:nowrap; }
.band .cap { font:500 40px/1.3 "IBM Plex Sans",sans-serif; }
.url { font:500 40px "IBM Plex Mono",monospace; color:var(--accent); }
"""
FONTS = (
    '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Condensed:'
    'wght@600;700&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@500&display=swap">'
)


def page(body: str) -> str:
    return f'<!doctype html><html lang="fr"><head><meta charset="utf-8">{FONTS}<style>{CSS}</style></head><body>{body}</body></html>'


def card(eyebrow: str, title: str, sub: str = "", extra: str = "") -> str:
    sub_html = f'<p class="sub">{sub}</p>' if sub else ""
    return page(f'<div class="stage"><span class="eyebrow">{eyebrow}</span><h1>{title}</h1>{sub_html}{extra}</div>')


def shot(image: Path, tag: str, caption: str) -> str:
    return page(
        f'<div class="shotstage"><div class="frame"><img src="{image.as_uri()}"></div>'
        f'<div class="band"><span class="tag">{escape(tag)}</span><span class="cap">{caption}</span></div></div>'
    )


def crop(src: Path, box: tuple[int, int, int, int], name: str) -> Path:
    dst = WORK / name
    Image.open(src).crop(box).save(dst)
    return dst


KPIS = (
    '<div class="kpis">'
    + "".join(
        f'<div class="kpi"><b>{v}</b><span>{t}</span></div>'
        for v, t in [
            ("21", "contrôles SQL : qualité, RGPD, catalogue"),
            ("12 → 18", "contrôles conformes avant / après"),
            ("100 %", "consentements tracés après remédiation"),
            ("1,4 s", "pour 501 513 événements"),
            ("40", "tests pytest verts"),
        ]
    )
    + "</div>"
)


def scenes() -> list[tuple[str, str, str, float]]:
    L = IMG / "livrables"
    rapport = crop(IMG / "demo-rapport.png", (40, 0, 1240, 680), "rapport-haut.png")
    return [
        ("01-titre", card("Gouvernance des données · cas Spotify", "Du diagnostic au plan d'action, <em>puis à la preuve</em>.",
                          "Mission de conseil pour un comité exécutif · Bloc 1 RNCP 38777"),
         "Gouvernance des données, le cas Spotify. Une mission de conseil pour un comité exécutif : du diagnostic au plan d'action, puis à la preuve.", 1.04),
        ("02-probleme", card("Le problème", "Des silos, et une exposition réglementaire mondiale",
                             extra="<ul><li>450 millions d'utilisateurs, 180 pays</li>"
                                   "<li>Marketing, produit, contenu : chacun ses données</li>"
                                   "<li>RGPD : jusqu'à 4 % du chiffre d'affaires mondial</li></ul>"),
         "Quatre cent cinquante millions d'utilisateurs, cent quatre-vingts pays, des données éclatées entre les équipes. "
         "Et un risque réglementaire qui peut atteindre quatre pour cent du chiffre d'affaires mondial.", 1.03),
        ("03-diagnostic", shot(L / "slide-03.png", "Diagnostic", "Neuf dimensions de maturité, notées de 1 à 5."),
         "D'abord, un diagnostic : neuf dimensions de maturité, notées de un à cinq. Un projet bien posé, pas encore une organisation mature.", 1.08),
        ("04-organisation", shot(IMG / "architecture-1.png", "Organisation", "Sponsor, CDO, comité, DPO et un Data Steward par domaine."),
         "Ensuite, une organisation : un sponsor exécutif, un Chief Data Officer, un comité transverse, "
         "un délégué à la protection des données, et un responsable de la donnée par domaine métier.", 1.10),
        ("05-politique", shot(L / "politique-classification.png", "Politique", "Neuf principes, quatre niveaux de classification."),
         "Puis une politique : neuf principes, et quatre niveaux de classification, du public au restreint, chacun avec ses contrôles.", 1.06),
        ("06-plan", shot(L / "slide-10.png", "Plan", "Pilote Marketing de 6 mois, puis trois vagues."),
         "Enfin un plan : un pilote de six mois sur les données d'engagement du marketing, puis trois vagues de déploiement, avec un budget sourcé.", 1.08),
        ("07-demo", card("Démonstrateur exécutable", "La politique, <em>exécutée en SQL</em>.",
                         "Données 100 % synthétiques, défauts injectés à des taux connus.", KPIS),
         "Ce dépôt va plus loin. La politique devient vingt et un contrôles SQL, exécutés sur un jeu de données d'exemple, "
         "entièrement synthétique. Après remédiation, dix-huit contrôles sont conformes, et cent pour cent des consentements sont tracés.", 1.03),
        ("08-rapport", shot(rapport, "Rapport", "Avant / après, et ce qui reste rouge."),
         "Trois contrôles restent rouges, volontairement : des demandes d'accès traitées en retard, des violations notifiées hors délai. "
         "Ce sont des défauts de processus ; le code refuse de les maquiller.", 1.10),
        ("09-audit", card("Audit des livrables", "Relire ses propres chiffres <em>avant le comité</em>.",
                          extra="<ul><li class='bad'>Maturité : 2,4 annoncé, 2,33 calculé dans le document</li>"
                                "<li class='bad'>6 notes sur 9 diffèrent entre le graphique et l'analyse</li>"
                                "<li class='bad'>Intégration « 30 à 50 % » appliquée à 30 % seulement</li>"
                                "<li class='warn'>« 14 contrôles de conformité » : non traçables</li></ul>"),
         "Un audit automatique relit aussi les livrables eux-mêmes. Il trouve des écarts : une moyenne de maturité annoncée à deux virgule quatre, "
         "calculée à deux virgule trois dans le document, et une marge d'intégration sous-estimée. Ils sont signalés, sans retoucher les fichiers remis au jury.", 1.03),
        ("10-fin", card("Gouvernance des données · Spotify", "Les livrables, le code et les mesures sont publics.",
                        extra='<p class="url">github.com/PDUCLOS/BLOC1-SPOTIFY</p><p class="sub">Patrice Duclos · Analytics Engineer · Architecte IA</p>'),
         "Les livrables, le démonstrateur et les mesures sont sur GitHub.", 1.04),
    ]


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def render_png(html: str, png: Path) -> None:
    src = png.with_suffix(".html")
    src.write_text(html, encoding="utf-8")
    run([EDGE, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1",
         f"--user-data-dir={WORK / 'edge-profile'}", "--window-size=1920,1080",
         "--virtual-time-budget=4000", f"--screenshot={png}", src.as_uri()])


def narrate(text: str, wav: Path) -> None:
    txt = wav.with_suffix(".txt")
    txt.write_text(text, encoding="utf-8")
    ps = (
        "Add-Type -AssemblyName System.Speech;"
        "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer;"
        "$s.SelectVoice('Microsoft Hortense Desktop'); $s.Rate = 1;"
        f"$s.SetOutputToWaveFile('{wav}');"
        f"$s.Speak([IO.File]::ReadAllText('{txt}', [Text.Encoding]::UTF8)); $s.Dispose()"
    )
    run(["powershell", "-NoProfile", "-Command", ps])


def duration(path: Path) -> float:
    out = subprocess.run([FFPROBE, "-v", "error", "-show_entries", "format=duration", "-of", "json", str(path)],
                         check=True, capture_output=True, text=True).stdout
    return float(json.loads(out)["format"]["duration"])


def encoder() -> list[str]:
    probe = subprocess.run([FFMPEG, "-hide_banner", "-encoders"], capture_output=True, text=True).stdout
    if "h264_nvenc" in probe:
        return ["-c:v", "h264_nvenc", "-preset", "p6", "-cq", "24", "-b:v", "0"]
    return ["-c:v", "libx264", "-preset", "medium", "-crf", "23"]


def clip(png: Path, wav: Path, zoom: float, mp4: Path) -> float:
    dur = duration(wav) + PAD_S
    frames = int(dur * FPS)
    step = (zoom - 1.0) / frames
    vf = (
        f"[0:v]scale=3840:2160,zoompan=z='min(1+{step:.6f}*on,{zoom})':d={frames}:"
        f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1920x1080:fps={FPS},"
        f"fade=t=in:st=0:d=0.45,fade=t=out:st={dur - 0.45:.2f}:d=0.45,format=yuv420p[v];"
        f"[1:a]adelay=350|350,apad,atrim=0:{dur:.2f},aformat=sample_rates=48000:channel_layouts=stereo[a]"
    )
    run([FFMPEG, "-y", "-loop", "1", "-i", str(png), "-i", str(wav), "-filter_complex", vf,
         "-map", "[v]", "-map", "[a]", "-t", f"{dur:.2f}", *encoder(), "-c:a", "aac", "-b:a", "160k", str(mp4)])
    return dur


def main() -> int:
    WORK.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    clips, total = [], 0.0
    for name, html, text, zoom in scenes():
        png, wav, mp4 = WORK / f"{name}.png", WORK / f"{name}.wav", WORK / f"{name}.mp4"
        render_png(html, png)
        narrate(text, wav)
        total += clip(png, wav, zoom, mp4)
        clips.append(mp4)
        print(f"  {name}: {total:5.1f} s")

    concat = WORK / "concat.txt"
    concat.write_text("".join(f"file '{c.as_posix()}'\n" for c in clips), encoding="utf-8")
    joined = WORK / "joined.mp4"
    run([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", str(concat), "-c", "copy", str(joined)])

    # Nappe sonore synthétisée (accord de quinte, battement lent) mixée sous la voix.
    pad = (
        f"aevalsrc='0.05*sin(2*PI*110*t)*(0.6+0.4*sin(2*PI*0.08*t))+0.035*sin(2*PI*164.81*t)"
        f"+0.03*sin(2*PI*220*t)*(0.6+0.4*sin(2*PI*0.05*t+1))+0.02*sin(2*PI*329.63*t)':"
        f"s=48000:d={total:.2f},afade=t=in:d=2,afade=t=out:st={total - 3:.2f}:d=3,"
        f"lowpass=f=900,aformat=channel_layouts=stereo,volume=0.55[pad]"
    )
    final = OUT / "gouvernance-spotify-promo.mp4"
    run([FFMPEG, "-y", "-i", str(joined), "-filter_complex",
         f"{pad};[0:a][pad]amix=inputs=2:duration=first:dropout_transition=0:normalize=0,loudnorm=I=-16:TP=-1.5[a]",
         # Réencodage x264 pour tenir sous 15 Mo (GitHub Pages) : images fixes, zoom lent.
         "-map", "0:v", "-map", "[a]", "-c:v", "libx264", "-preset", "slow", "-crf", "26", "-tune", "stillimage",
         "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k",
         "-movflags", "+faststart", str(final)])
    shutil.copy(WORK / "01-titre.png", OUT / "poster.png")
    print(f"Vidéo : {final} ({total:.1f} s, {final.stat().st_size / 1e6:.1f} Mo)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
