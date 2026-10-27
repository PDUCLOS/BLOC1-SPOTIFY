"""Jeu de données synthétique du périmètre pilote (Marketing / User Engagement Data).

Aucune donnée réelle : identifiants séquentiels, e-mails en @example.com, graine fixe.
Des défauts sont injectés à des taux connus (``DEFECTS``) pour que chaque contrôle ait
quelque chose à trouver, et pour que les tests puissent vérifier qu'il le trouve.
"""

from __future__ import annotations

import csv
import hashlib
import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

AS_OF = datetime(2026, 5, 31, 12, 0, 0)  # date de référence : celle de la politique v1.0
COUNTRIES = ["FR", "DE", "ES", "IT", "SE", "GB", "US", "BR", "MX", "JP", "IN", "SG"]
EVENT_TYPES = ["play", "play", "play", "skip", "like", "add_playlist"]

# Taux de défauts injectés (part des lignes concernées).
DEFECTS = {
    "users.country_missing": 0.06,
    "users.country_invalid": 0.01,
    "users.birth_year_missing": 0.08,
    "users.email_invalid": 0.015,
    "users.consent_ts_missing": 0.02,      # consentement « oui » sans preuve horodatée
    "events.orphan_user": 0.008,
    "events.negative_ms": 0.005,
    "events.future_ts": 0.002,
    "events.duplicate_id": 0.003,
    "events.lineage_missing": 0.005,
    "events.beyond_retention": 0.01,
    "audience.no_consent": 0.03,           # exporté vers la campagne sans consentement
    "audience.raw_email": 0.02,            # e-mail en clair au lieu du hash
}


@dataclass
class Dataset:
    tables: dict[str, list[dict]] = field(default_factory=dict)

    def write_csv(self, folder: Path) -> dict[str, Path]:
        folder.mkdir(parents=True, exist_ok=True)
        paths = {}
        for name, rows in self.tables.items():
            path = folder / f"{name}.csv"
            with path.open("w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
                w.writeheader()
                w.writerows(rows)
            paths[name] = path
        return paths


def _ts(d: datetime | None) -> str:
    return d.strftime("%Y-%m-%d %H:%M:%S") if d else ""


def sha256(text: str) -> str:
    return hashlib.sha256(text.strip().lower().encode()).hexdigest()


def generate(n_users: int = 5000, events_per_user: int = 10, seed: int = 38777) -> Dataset:
    rnd = random.Random(seed)
    hit = lambda key: rnd.random() < DEFECTS[key]  # noqa: E731

    users, subs = [], []
    for i in range(1, n_users + 1):
        uid = f"U{i:07d}"
        country = rnd.choice(COUNTRIES)
        premium = rnd.random() < 0.44  # 200 M Premium / 450 M actifs, ordre de grandeur du cas
        if premium:
            subs.append({"user_id": uid, "plan": rnd.choice(["individual", "duo", "family"]), "billing_country": country})
        signup = AS_OF - timedelta(days=rnd.randint(30, 2500))
        consent = rnd.random() < 0.62
        consent_ts = signup + timedelta(minutes=rnd.randint(1, 600)) if consent else None
        email = f"user{i}@example.com"
        if hit("users.email_invalid"):
            email = f"user{i}.example.com"
        if hit("users.country_invalid"):
            country = rnd.choice(["France", "fr ", "XX"])
        elif hit("users.country_missing"):
            country = ""
        if consent and hit("users.consent_ts_missing"):
            consent_ts = None
        users.append({
            "user_id": uid, "email": email, "country": country,
            "birth_year": "" if hit("users.birth_year_missing") else rnd.randint(1950, 2010),
            "signup_date": signup.strftime("%Y-%m-%d"),
            "consent_marketing": "true" if consent else "false",
            "consent_ts": _ts(consent_ts), "consent_source": "cmp_web" if consent else "",
            "phone_number": f"+33 6 {rnd.randint(10, 99)} {rnd.randint(10, 99)} {rnd.randint(10, 99)} {rnd.randint(10, 99)}",
            "source_system": "crm", "ingested_at": _ts(AS_OF - timedelta(days=1)),
        })

    events, n = [], 0
    for u in users:
        for _ in range(events_per_user):
            n += 1
            ts = AS_OF - timedelta(minutes=rnd.randint(1, 60 * 24 * 365))
            if hit("events.beyond_retention"):
                ts = AS_OF - timedelta(days=rnd.randint(745, 900))  # > 24 mois
            elif hit("events.future_ts"):
                ts = AS_OF + timedelta(days=rnd.randint(1, 30))
            ev = {
                "event_id": f"E{n:09d}",
                "user_id": f"U{n_users + rnd.randint(1, 10**6):07d}" if hit("events.orphan_user") else u["user_id"],
                "event_ts": _ts(ts), "event_type": rnd.choice(EVENT_TYPES),
                "track_id": f"T{rnd.randint(1, 20000):06d}",
                "ms_played": -rnd.randint(1, 5000) if hit("events.negative_ms") else rnd.randint(0, 360000),
                "source_system": "" if hit("events.lineage_missing") else "event_bus",
                "ingested_at": _ts(AS_OF - timedelta(hours=2)),
            }
            events.append(ev)
            if hit("events.duplicate_id"):
                events.append(dict(ev))

    audience = []
    consenting = [u for u in users if u["consent_marketing"] == "true"]
    refusing = [u for u in users if u["consent_marketing"] == "false"]
    for u in rnd.sample(consenting, k=min(len(consenting), n_users // 4)):
        src = rnd.choice(refusing) if hit("audience.no_consent") else u
        audience.append({
            "user_id": src["user_id"], "campaign_id": f"CMP-2026-{rnd.randint(1, 6):02d}",
            "email_sha256": src["email"] if hit("audience.raw_email") else sha256(src["email"]),
            "exported_at": _ts(AS_OF - timedelta(days=rnd.randint(1, 20))),
        })

    dsar = []
    for k in range(1, 121):
        regime = "CCPA" if rnd.random() < 0.25 else "RGPD"
        received = AS_OF - timedelta(days=rnd.randint(1, 200))
        limit = 45 if regime == "CCPA" else 30
        delay = rnd.randint(2, limit - 2)
        if k in (7, 41, 88):          # traitées hors délai
            received = AS_OF - timedelta(days=rnd.randint(90, 200))
            delay = limit + rnd.randint(3, 20)
        closed = received + timedelta(days=delay)
        if k == 113:                  # ouverte et déjà hors délai
            received = AS_OF - timedelta(days=limit + 9)
            closed = None
        elif closed > AS_OF:          # encore en cours, dans les délais
            closed = None
        dsar.append({
            "request_id": f"DSAR-{k:04d}", "user_id": rnd.choice(users)["user_id"], "regime": regime,
            "request_type": rnd.choice(["acces", "effacement", "opposition", "portabilite"]),
            "received_at": _ts(received), "closed_at": _ts(closed),
        })

    incidents = []
    for k, (hours, personal) in enumerate([(20, True), (48, True), (90, True), (None, False), (30, True), (None, True)], 1):
        detected = AS_OF - timedelta(days=10 * k)
        incidents.append({
            "incident_id": f"INC-{k:03d}", "personal_data": "true" if personal else "false",
            "detected_at": _ts(detected), "notified_at": _ts(detected + timedelta(hours=hours) if hours else None),
        })

    return Dataset({"users": users, "events": events, "campaign_audience": audience,
                    "subscriptions": subs, "dsar_requests": dsar, "security_incidents": incidents})
