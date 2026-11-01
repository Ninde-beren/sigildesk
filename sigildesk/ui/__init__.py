"""Couche de présentation : les objets Qt que le QML lit et appelle.

Chaque classe est un `QObject` ou un `QAbstractListModel` exposé au QML par
`app.py` sous un nom de contexte (`app`, `theme`, `favorites`, `wallpapers`,
`weather`, `systemStatus`, `updates`, `openWindows`, `icons`, `webTiles`,
`localTiles`). Ces objets ne contiennent pas de règle métier : ils appellent
`domain` et `infra`, puis traduisent le résultat en propriétés, signaux et
messages prêts à afficher. Rien ici n'est importé par `domain` ni `infra`.
"""
