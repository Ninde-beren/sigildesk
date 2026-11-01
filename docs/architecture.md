# Architecture de SigilDesk

SigilDesk est une fenêtre Qt Quick plein écran posée au-dessus de LXQt. Elle ne
remplace rien : elle lance les applications déjà installées et s'efface devant
elles. Ce document décrit comment le code est rangé, ce qui ne doit jamais
changer, et comment l'étendre.

## Vue d'ensemble

```
            QML (sigildesk/qml)            l'écran : tuiles, panneaux, dialogues
                    ▲  propriétés, signaux, slots
                    │
            ui/     objets Qt exposés au QML (QObject, QAbstractListModel)
                    │  appelle
            infra/  accès au système : fichiers, processus, réseau, /sys, session LXQt
                    │  appelle
            domain/ règles métier pures : validation, catalogue, commandes, libellés
```

Les flèches ne remontent jamais : `domain` n'importe que la bibliothèque
standard ; `infra` peut importer `domain` ; `ui` peut importer les deux ;
`app.py` assemble le tout. `tests/test_architecture.py` lit les imports de
chaque module et refuse un croisement.

| Couche | Ce qu'on y trouve | Ce qu'on n'y trouve pas |
|---|---|---|
| `domain/` | dataclasses, fonctions pures, validation, messages d'erreur en français | PySide6, `open()`, `subprocess`, réseau |
| `infra/` | une petite API par ressource extérieure, avec un point d'injection (`which`, `runner`, `starter`, `now`) | types QML, règles métier |
| `ui/` | propriétés `Property(...)`, `Signal`, `Slot`, modèles de liste | décisions : elles sont demandées à `domain` et `infra` |

## Le démarrage, pas à pas (`app.py`)

1. `cli.parse_args` : options. `--version` et `--doctor` s'arrêtent là, sans fenêtre.
2. `infra.paths.UserPaths` : où lire et écrire chez l'utilisateur (XDG ; `--root` regroupe tout pour les essais).
3. `infra.single_instance` : un second lancement réveille le premier et quitte.
4. `infra.config_store.ConfigStore.load()` : réglages validés par `domain.settings`, migrés si besoin, mis de côté s'ils sont illisibles.
5. Construction des objets `ui/`, chacun recevant ses dépendances par le constructeur (jamais de global).
6. `QQmlApplicationEngine` : chaque objet est exposé sous un nom (`app`, `theme`, `favorites`, `wallpapers`, `weather`, `systemStatus`, `updates`, `openWindows`, `icons`, `webTiles`, `localTiles`), puis `Main.qml` est chargé.
7. Après l'affichage : première météo (`QTimer.singleShot(0)`), surveillance des mises à jour 20 s plus tard.

## Flux typiques

**Clic sur une tuile.** `Tile.qml` appelle `app.openTile("youtube")`. Le
contrôleur (`ui.controller`) : la tuile existe (`domain.catalog.tile`) ; si
elle est « à régler » (messagerie absente), il ouvre les Paramètres ; si une
fenêtre correspondante est déjà ouverte (`infra.window_manager`), il la ramène ;
sinon, garde anti-double-clic (5 s), puis `infra.launcher.open_url`, qui demande
à `domain.commands.CommandBuilder` la commande exacte (programme résolu par
`infra.processes.find_program`, adresse normalisée par `domain.urls`) et la
passe à `QProcess.startDetached`. Le QML reçoit un code court (« ok »,
« retour », « attente », « reglage », « erreur ») et un message `toast`.

**Changement d'un réglage.** Toute écriture suit le même chemin : copie du
document (`ConfigStore.copy()`), modification, `ConfigStore.replace()`, qui
valide par `domain.settings.validate` et écrit atomiquement
(`infra.files.atomic_write_json`). Si la validation ou l'écriture échoue,
rien ne change en mémoire et un message revient au QML.

**Météo.** `ui.weather_service` affiche d'abord le cache
(`infra.weather_cache`), puis demande à `infra.http_client` l'URL fournie par
`infra.open_meteo` ; la réponse est traduite en `domain.weather.Conditions`,
mise en cache, et les propriétés changent. Un numéro de génération écarte une
réponse arrivée après un changement de ville. Tout est asynchrone sur la boucle
Qt : aucun fil.

## Invariants (ne pas casser)

- **Aucune commande ne vient du JSON.** Les programmes possibles sont dans
  `domain/commands.py` et `domain/catalog.py`. La configuration ne choisit que
  parmi des listes et fournit des adresses, toutes passées par
  `normalize_web_url` (http/https seulement, donc jamais prises pour une option).
- **Jamais de shell.** `QProcess.startDetached(programme, [arguments])` et
  `subprocess.run([argv])`, toujours en liste.
- **Schéma fermé.** Clé inconnue, type inattendu, valeur hors liste : document
  refusé, mis de côté, valeurs par défaut. Un fichier d'une version future n'est
  jamais écrasé.
- **SigilDesk n'écrit que chez lui** : `~/.config/sigildesk`,
  `~/.local/share/sigildesk`, `~/.local/state/sigildesk`, `~/.cache/sigildesk`,
  plus son lanceur, son entrée de menu, son icône et son autostart, tous
  marqués. Les scripts refusent d'écraser un fichier du même nom qui n'est pas
  le leur. Seule exception, voulue et réversible : `lock_screen_before_power_actions`
  dans `~/.config/lxqt/session.conf` (voir `scripts/session-lock.py`).
- **Pas de root à l'exécution** ; seul `scripts/install-system-deps.sh` utilise
  sudo, après confirmation.
- **Extinction par la session** (`org.lxqt.session.powerOff`), jamais forcée.
- **Aucune donnée sensible** : ni mot de passe, ni identifiant, ni favicon
  téléchargé ; la seule donnée qui sort est la ville de la météo (Open-Meteo,
  CC BY 4.0, usage non commercial).

## Tests

`./run-tests.sh` (unittest, rendu hors écran, ~25 s) :

- **domain** : valeurs en entrée, valeurs en sortie, aucun montage ;
- **infra** : faux `which`, faux `runner`, arborescence `/sys` factice, faux
  client HTTP ; jamais le vrai réseau ni le vrai système ;
- **ui** : une seule `QGuiApplication` pour la suite (`tests/support.py`),
  propriétés lues par `property()` ;
- **mise en page** (`test_layout`) : l'application réelle, lancée avec
  `--dump-geometry`, mesure ses zones `geo_*` à 1366×768 et 1024×600 ;
- **scripts** (`test_scripts`) : installation, autostart, désinstallation dans
  un dossier personnel factice ;
- **architecture** (`test_architecture`) : les imports respectent les couches.

`scripts/test-lubuntu.sh` rejoue le tout dans un conteneur Ubuntu 26.04 avec le
PySide6 6.10 de la distribution, celui de l'ASUS : Qt 6.10 refuse des choses que
6.12 accepte (dépendances circulaires entre fichiers QML, par exemple).

## Comment étendre

**Une tuile.** Ajouter un `TileSpec` dans `domain/catalog.py` et son icône dans
`resources/icons/`. Une tuile web a son adresse dans `web` du schéma
(`domain/settings.py` + `config/default.json`, donc `SCHEMA_VERSION` + 1 et une
migration) ; une tuile locale, son dossier dans `folders`. Le QML n'a rien à
savoir : il affiche le modèle.

**Un réglage.** Clé dans `config/default.json`, validation dans
`domain/settings.py`, `SCHEMA_VERSION` + 1, migration dans `MIGRATIONS`,
propriété et slot dans `ui/controller.py`, carte dans `SettingsPanel.qml`.

**Un fournisseur météo.** Une classe qui respecte `domain.weather.WeatherProvider`
(quatre méthodes, aucune requête), instanciée dans `app.py` à la place
d'`OpenMeteo`. Cache, service et QML ne changent pas.

**Une autre ressource système.** Un module dans `infra/` avec sa fonction
d'accès injectable, un module dans `ui/` qui l'expose au QML si l'écran en a
besoin, l'assemblage dans `app.py`.

## Pièges connus

- Les propriétés Qt d'une classe PySide6 se déclarent dans le corps de la
  classe ; ajoutées par `setattr`, le QML ne les voit pas.
- `QTimer.singleShot(ms, objet.methode)` ne retient qu'une référence faible vers
  `objet` : un veilleur sans parent ni référence est ramassé avant de sonner
  (`devtools.ReadyWatcher` est un QObject avec parent pour cette raison).
- `T.Popup` (QtQuick.Templates) n'a pas de taille implicite : la donner, sinon le
  fond fait 0 px.
- `test_layout` lit les `objectName` `geo_*` : les garder en modifiant le QML.
