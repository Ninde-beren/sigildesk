"""Couche métier : les règles de SigilDesk, sans Qt, sans fichier, sans réseau.

Tout ce qui est ici se teste avec de simples valeurs : adresses web
(`urls`), schéma des réglages (`settings`), favoris (`favorites`), raccourci de
maintenance (`shortcuts`), commandes à lancer (`commands`), météo (`weather`),
fenêtres ouvertes (`windows`) et le catalogue de ce que l'accueil propose
(`catalog`). Ces modules n'importent que la bibliothèque standard et d'autres
modules de `domain`. Les couches `infra` et `ui` s'appuient dessus, jamais
l'inverse.
"""
