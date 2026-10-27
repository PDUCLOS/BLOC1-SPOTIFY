# Gouvernance des données — Spotify : fiche de vérification pour le portfolio

Branche : `feat/vitrine-gouvernance-spotify` · dépôt https://github.com/PDUCLOS/BLOC1-SPOTIFY
Session du 27/10/2026, machine Windows 11 (Ryzen 9 3900X, 32 Go), Python 3.12.3, DuckDB 2.0.0.
Tout chiffre ci-dessous a été **mesuré ou recompté dans cette session**. Ce qui ne l'a pas été est écrit comme tel.

## 1. Nature du projet

Dossier de conseil (Bloc 1 RNCP 38777) : six fichiers remis au jury, aucun code à l'origine.

| Fichier | Contenu vérifié |
|---|---|
| `01_Evaluation_Maturite_Data.docx` | 9 dimensions notées 1 à 5, échelle définie (inexistant → opérationnel), moyenne écrite « environ 2,3 » |
| `02a_Organigramme_Gouvernance.pdf` | Sponsor CEO/COO, CDO, comité (mensuel puis trimestriel), DPO, Engineering/RSSI, Juridique & Privacy, 4 Data Stewards |
| `02b_Note_Argumentation_Organigramme.docx` | Justification de chaque rôle par un document source, réponses aux objections |
| `02c_Politique_Gouvernance_Donnees.docx` | 9 principes, 4 niveaux de classification, RGPD / CCPA / PCI-DSS, 7 KPIs, 3 phases |
| `03_Plan_Implementation_Gouvernance.docx` | Center of Excellence, stack outillée, pilote Marketing 6 mois, 3 vagues (M7–M18), risques, budget sourcé |
| `04_Presentation_Comite_Executif.pptx` | 14 slides, décision demandée |

Le « traitement complet » a été adapté : pas de service à conteneuriser, donc un **démonstrateur exécutable** de la politique et un **audit chiffré des livrables**, plutôt que du code inventé.

## 2. Ce qui a été ajouté et exécuté

| Élément | Résultat mesuré |
|---|---|
| `python -m gouvernance` (5 000 utilisateurs, 50 148 événements synthétiques, graine 38777) | 21 contrôles ; **12 conformes avant remédiation, 18 après** ; génération 1,37 s, contrôles 0,82 s, remédiation + recontrôle 0,46 s, audit des livrables 0,35 s |
| Passage à l'échelle `--users 50000` (501 513 événements) | contrôles 1,36 s ; remédiation + recontrôle 1,37 s ; génération Python des CSV 12,0 s |
| `python -m pytest` | **40 tests verts** (4,7 s) |
| `audit_livrables.py` sur les vrais fichiers | 12 points : **7 cohérents, 5 signalés** (3 écarts chiffrés, 1 non traçable, 1 à harmoniser) |
| `scripts/build_drawio.py` | 4 pages draw.io, exportées en PNG par draw.io CLI et relues visuellement |
| `scripts/promo_video.py` | vidéo 1920×1080, **115,1 s, 11,5 Mo** (H.264 + AAC), narration Hortense |

KPIs du démonstrateur (données synthétiques, défauts injectés à des taux connus — ils mesurent le démonstrateur, **pas Spotify**) :

| KPI (source) | Avant | Après | Cible |
|---|---|---|---|
| Score qualité, moyenne des 11 contrôles qualité (politique §6.2) | 98,3 % | 98,7 % | ≥ 95 % — atteint |
| Cellules vides sur colonnes critiques (plan §4.6) | 0,42 % | 0,36 % | −10 % — atteint (−14,9 %) |
| Consentements tracés (plan §4.6) | 97,9 % | 100,0 % | 100 % — atteint |
| DSAR dans les délais légaux (politique §6.2) | 96,5 % | 96,5 % | 100 % — non atteint (volontaire) |
| Violations notifiées sous 72 h (RGPD art. 33) | 60,0 % | 60,0 % | 100 % — non atteint (volontaire) |

Remédiation comptée : 147 pays complétés depuis les abonnements, 65 consentements sans preuve traités comme absents, 764 événements en quarantaine, 144 doublons supprimés, 478 événements purgés (> 24 mois), 55 lignes d'audience retirées faute de consentement, 29 e-mails en clair pseudonymisés, 1 colonne hors catalogue supprimée.

## 3. Écarts entre la fiche portfolio (`build/projects.py`, slug `gouvernance-spotify`) et le dépôt

| Affirmation de la fiche | Constat | Proposition |
|---|---|---|
| KPI « ~2,4/5 maturité initiale » | Le document d'évaluation calcule 21/9 = **2,33** (« environ 2,3 »). 2,4 est la moyenne du graphique de la slide 3 (22/9 = 2,44), dont **6 notes sur 9 diffèrent** du document (gouvernance 3→2, architecture 2→3, conformité 3→2, sécurité 2→3, intégration 3→2, Analytics & BI 2→4). Même graphique dans la version V4 archivée. | « ≈ 2,3/5 » (valeur de l'analyse écrite), ou mentionner l'écart |
| Étape « gouvernance, conformité et intégration au niveau « cadré » » | Exact selon le document 01 ; **contredit par le graphique** de la présentation (ces trois dimensions à 2). | Garder, c'est la source écrite |
| KPI « ×3 ROI visé » | Slide 12 : « ROI > 3× », **aucun calcul** dans le dépôt. | « ROI > 3× annoncé (non chiffré) » ou retirer |
| KPI « 4 livrables » | 6 fichiers pour 4 étapes. | « 6 livrables (4 étapes) » |
| `langs_note` « Projet de conseil, sans code. » | Faux sur cette branche : démonstrateur Python + SQL, 40 tests. | « Dossier de conseil + démonstrateur Python / SQL (DuckDB) » |
| `band` « pilote 6 mois (marketing) → modèle centralisé → Centre d'excellence » | Slides 7-8 : centralisé **pendant** le pilote (M0–M12), puis CoE (M12–M24). | « Pilote 6 mois (Marketing, pilotage centralisé) → 3 vagues jusqu'à M18 → Center of Excellence » |
| Tout le reste (450 M, 4 %, 9 dimensions, rôles, stack, KPIs −10 % / 100 % / 24 h, pilote engagement Marketing) | Retrouvé mot pour mot ou chiffre pour chiffre dans 01, 02a, 03, 04. | — |

## 4. Écarts internes aux livrables (signalés, non corrigés : ce sont les versions jury)

1. **Maturité** : voir ci-dessus (A01, A02).
2. **Budget** (B03) : la ligne « Intégration & services : +30–50 % des licences » vaut 80–130 K$, soit 30 % des deux bornes. Avec 30 % de la borne basse et 50 % de la haute : 81–215 K$, donc un pilote à **351–645 K$** au lieu de 350–560 K$ (haut de fourchette sous-estimé de 85 K$). Sous-totaux licences exacts : 270–430 K$ ; 2,145–5,790 M$ arrondis à 2,1–5,8 M$.
3. **« 14 contrôles de conformité »** (slide 5, C04) : aucune liste ni « matrice de conformité » (citée slide 14) dans le dépôt ; la section 4 de la politique compte 13 rubriques.
4. **Calendrier** (D01) : plan terminé à M18, politique à M24 ; bascule CoE en phase 2 (7–12 mois) dans la politique, à M12 dans les slides.
5. Points de vigilance de lecture (non automatisés) : rattachement du DPO au CDO justifié par l'art. 38 RGPD, qui demande un rapport « au niveau le plus élevé de la direction » ; « incidents traités sous 72 heures » (le RGPD impose une notification sous 72 h) ; DSAR RGPD noté 30 jours (le texte dit un mois, prolongeable).
6. Cohérents : 9 principes, 4 niveaux, 7 KPIs, 14 slides, total pilote = licences + intégration telle qu'écrite.

## 5. Limites et non vérifié

- Recommandations (organisation, outils, budget) **non mises en œuvre** ; prix éditeurs repris des sources citées dans le plan, **non revérifiés** (sites éditeurs / Vendr non consultés).
- Le démonstrateur **simule** Databricks (DuckDB), dbt/Talend (requêtes SQL à la convention des tests dbt) et Collibra (`catalog.toml`). Aucun de ces outils n'a été installé ni testé.
- Le « score qualité » est une moyenne de taux de réussite : il reste à 98 % alors que le contrôle « année de naissance » est à 91,7 %.
- **Docker / Kubernetes : non fournis, volontairement** — pas de service, pas d'état, un traitement par lots de 2 s. Expliqué dans la vitrine (section « Pourquoi ni Docker ni Kubernetes »).
- GitHub Pages : **non vérifié en ligne** (la branche n'est pas fusionnée et la configuration Pages du dépôt n'a pas été touchée). Vérifié en local : rendu desktop (Edge headless 1280 px) et mobile (émulation 375 px, aucun débordement horizontal).
- La vidéo n'a été contrôlée que par extraction d'images et `ffprobe` ; pas d'écoute humaine de la narration.

## 6. Médias produits (chemins relatifs à `docs/`)

| Média | Fichier |
|---|---|
| Vitrine | `index.html` |
| Vidéo + affiche | `video/gouvernance-spotify-promo.mp4` (115 s, 11,5 Mo) · `video/poster.png` |
| Schémas | `architecture.drawio` (4 pages) · `img/architecture-1.png` organisation · `-2` flux et outillage · `-3` feuille de route · `-4` démonstrateur |
| Captures des livrables (export PowerPoint / Word, sans retouche) | `img/livrables/slide-01…14.png` (11 slides), `organigramme.png`, `politique-classification.png`, `plan-budget.png`, `evaluation-p1.png` |
| Rapport du démonstrateur | `demo/rapport.html` · `demo/rapport.json` · capture `img/demo-rapport.png` |

Visuel conseillé pour la carte portfolio : `img/livrables/slide-06.png` (organigramme de la présentation) ou `img/architecture-1.png`.

## 7. Extraits exacts (pour citation)

- Document 01, §2 : « Score moyen : autour de 2,3 sur 5, à mi-chemin entre Identifié et Cadré. »
- Slide 3 : « MOYENNE 2,4 / 5 — Niveau « Identifié » à « Cadré » »
- Slide 12 : « VALEUR ATTENDUE — ROI > 3× »
- Plan 03, §4.6 : « Score qualité des données | -10 % de données manquantes | Audit Talend M1 vs M6 »
- Plan 03, annexe A : « Intégration & services (an 1) | +30–50 % des licences | 80–130 K$ »
- Slide 5 : « 9 principes · 4 niveaux de classification · 14 contrôles de conformité · 7 KPIs de pilotage »
- Slide 14 : « Sécuriser le budget pilote ≈ 350–560 K$ (licences + intégration) + équipe CoE de 4 à 6 ETP »

## 8. Proposition de textes pour la fiche

- `kpis` : `("9", "dimensions évaluées"), ("≈ 2,3/5", "maturité initiale"), ("21", "contrôles exécutables"), ("40", "tests")`
- `langs_note` : « Dossier de conseil (Word, PDF, PowerPoint) + démonstrateur Python / SQL DuckDB sur données synthétiques. »
- `limits` à ajouter : « Démonstrateur sur données synthétiques ; outils cibles simulés, non déployés. » · « Écarts relevés entre la présentation et le document d'évaluation (2,4 vs 2,3), signalés et non corrigés dans les livrables jury. »
- Force à ajouter : « <strong>Rigueur</strong> : un audit automatique relit les chiffres des livrables avant le comité. »
