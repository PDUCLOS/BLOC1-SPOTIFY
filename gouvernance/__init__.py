"""Démonstrateur de gouvernance des données — pilote Marketing (cas Spotify, Bloc 1 RNCP 38777).

Ce paquet n'est pas un livrable de la certification : il rend exécutables, sur des
données 100 % synthétiques, les règles écrites dans la politique (02c) et le plan (03).

- generate         : jeu de données synthétique du périmètre pilote, défauts injectés connus
- catalog.toml     : catalogue du pilote (propriétaire, classification, base légale, rétention)
- checks           : contrôles qualité (4 dimensions) et conformité RGPD / CCPA, en SQL DuckDB
- remediate        : nettoyage et enrichissement, pour mesurer un « avant / après »
- audit_livrables  : cohérence chiffrée entre les livrables Word / PowerPoint du dépôt
- report           : rapport JSON + tableau de bord HTML
"""

__version__ = "0.1.0"
