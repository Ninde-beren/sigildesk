# CLAUDE.md — sigildesk-app

Launcher plein écran PySide6 / Qt Quick pour Lubuntu 26.04 / LXQt (ASUS
E402SA). Python 3, QML, aucun serveur web, aucune WebEngine, pas de React/MUI.

## Périmètre

Ne rien lire ni modifier hors de `sigildesk/` (le dossier projet) sans demander.
Le cahier des charges est dans `../docs/`. Les documents livrés à l'utilisateur
(guide, récupération, tests manuels, conformité) sont dans `docs/` ici.

## Règles qui ne se discutent pas

- SigilDesk ne modifie jamais la session, LXQt (fond, panneau, raccourcis), le
  gestionnaire de fenêtres, SDDM ou GRUB. Il n'écrit que dans
  `~/.config/sigildesk`, `~/.local/share/sigildesk`, `~/.local/state/sigildesk`,
  son lanceur, son entrée de menu, son icône et son fichier d'autostart, tous
  marqués (`X-SigilDesk-Managed=true`, `# SigilDesk launcher`).
- Trois couches, vérifiées par `tests/test_architecture.py` : `domain/` (métier
  pur, ni PySide6, ni fichier, ni réseau), `infra/` (système : peut importer
  `domain`), `ui/` (QObject exposés au QML : peut importer les deux). Aucune
  règle métier dans `ui`, aucun import de `ui` ailleurs. `app.py` assemble.
  Voir `docs/architecture.md`.
- Aucune commande ne vient du JSON. Les programmes sont listés dans
  `domain/commands.py` / `domain/catalog.py`, résolus par
  `infra.processes.find_program` (`which`, plus `/snap/bin` pour Chromium),
  lancés par `infra.launcher` via `QProcess.startDetached(programme, arguments)`.
  Jamais de shell.
- Toute adresse passe par `domain.urls.normalize_web_url` (http/https uniquement).
- La configuration est un schéma fermé (`domain.settings.validate`) : une
  nouvelle clé, ou un élargissement des valeurs acceptées, impose d'incrémenter
  `SCHEMA_VERSION` et d'écrire la migration dans `MIGRATIONS` (version 3 depuis
  le 2026-11-01 : `folders.*` accepte un chemin absolu ; v2 du 2026-10-28 :
  météo, noms sous les icônes). Le fichier lui-même est l'affaire de
  `infra.config_store`.
- Météo : métier (`domain/weather.py`), fournisseur (`infra/open_meteo.py`),
  cache (`infra/weather_cache.py`), service Qt (`ui/weather_service.py`), QML
  (`WeatherWidget.qml`) restent séparés. Aucune requête réseau dans les tests :
  `--no-network` pour l'application, faux client HTTP pour le service.
- Extinction et redémarrage : une seule confirmation (celle de SigilDesk), puis
  `org.lxqt.session.powerOff`/`reboot` par D-Bus (vérifié dans Lubuntu 26.04),
  repli `lxqt-leave`, sinon guide. Jamais d'arrêt forcé.
- Mises à jour : SigilDesk n'installe rien ; il observe (`infra/updates.py`,
  `ui/update_monitor.py`) et propose de redémarrer. Le réglage système vit dans
  `data/52sigildesk-mises-a-jour`, posé par `install-system-deps.sh`.
- Fenêtres ouvertes : `domain/windows.py`, `infra/window_manager.py`,
  `ui/windows_model.py` (wmctrl, X11). Elles vivent dans leur
  propre barre, en haut au centre du bandeau, jamais mêlées au dock (décision d'Antoine,
  2026-10-28). Une tuile ramène sa fenêtre si elle est déjà ouverte.
- Habillage Sigilys system : `branding/` (logo « Sceau » choisi le 2026-10-28,
  propositions et générateurs dans `branding/propositions/`) ;
  `scripts/build-branding.py` fabrique le thème Plymouth et l'icône du menu.
- Veille : sans verrouilleur installé, `install-user.sh` coupe le verrouillage
  LXQt avant la veille (`scripts/session-lock.py`, option 1 choisie par Antoine
  le 2026-10-28) ; c'est la seule écriture dans un réglage LXQt, réversible.
- Usage non commercial : c'est la licence de SigilDesk et la condition de l'API
  gratuite d'Open-Meteo. L'attribution « Open-Meteo.com (CC BY 4.0) » doit rester
  visible dans les Paramètres.
- La version n'existe qu'à un endroit : `sigildesk/__init__.py`.
- Pas d'installation silencieuse. `install-user.sh` active l'ouverture
  automatique (décision d'Antoine, 2026-11-01 ; `--sans-autostart` pour essayer
  à la main d'abord). Seul `scripts/install-system-deps.sh` utilise sudo, après
  confirmation ; `install-user.sh` et l'application, jamais.

## Commandes

```bash
./run.sh --windowed --size 1366x768        # lancer (venv .venv si présent)
./run-tests.sh                              # ~175 tests, ~25 s, rendu hors écran
scripts/test-lubuntu.sh                     # mêmes tests dans Ubuntu 26.04 (PySide6 6.10 de la distribution)
.venv/bin/python scripts/capture.py         # régénère docs/captures/
python3 scripts/vm-demo.py                  # VM ouverte sur l'accueil : enregistre la démo (build/video/)
python3 scripts/vm-demo.py --sequence noms  # puis la séquence « noms sous les icônes » (build/video/noms/)
.venv/bin/python scripts/video-montage.py [--court]   # vidéo LinkedIn 1080×1350, longue ou ~50 s (copie dans ../com/)
python3 scripts/build-icons.py              # régénère les icônes SVG
.venv/lib/python3*/site-packages/PySide6/qmllint --unqualified disable sigildesk/qml/Main.qml sigildesk/qml/components/*.qml
```

## Pièges connus

- Les propriétés Qt d'une classe PySide6 doivent être déclarées dans le corps
  de la classe : ajoutées après coup (`setattr`), le QML ne les voit pas.
- `T.Popup` (Templates) n'a pas de taille implicite : la donner (voir
  `ConfirmDialog.qml`), sinon le fond fait 0 px.
- Qt 6.10, celui de Lubuntu 26.04, refuse les dépendances circulaires entre
  fichiers QML, alors que 6.12 les accepte. Toujours repasser par
  `scripts/test-lubuntu.sh` avant de livrer.
- Le style Basic est imposé par `QT_QUICK_CONTROLS_STYLE`, sans
  `QtQuickControls2` côté Python : une dépendance de moins.
- `test_layout` lance l'application hors écran et lit les zones nommées
  `geo_*` : garder ces `objectName` en modifiant le QML.
- `QTimer.singleShot(ms, objet.methode)` ne retient qu'une référence faible vers
  `objet` : un veilleur sans parent ni référence est ramassé avant de sonner
  (`devtools.ReadyWatcher` est un QObject avec parent pour cette raison).
