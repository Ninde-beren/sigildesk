# Conformité — SigilDesk 1.0

État au 2026-11-01. **Testé** : vérifié par la suite automatique (172 tests)
dans deux environnements. Le premier est le venv de développement (PySide6 6.12,
Python 3.12). Le second est le conteneur Ubuntu 26.04 (`scripts/test-lubuntu.sh`),
avec PySide6 6.10.2 et Python 3.14 des paquets de la distribution, ceux de
Lubuntu 26.04. Le rendu y est fait hors écran. **À valider sur ASUS** : dépend
d'une vraie session LXQt, du matériel ou du jugement de l'utilisatrice ou de
l'utilisateur. Voir [tests-manuels.md](tests-manuels.md). **Non testé** :
rien ne le vérifie encore.

## Vérifié dans la VM Lubuntu 26.04.1 (session live LXQt, 2026-10-28)

Avec `scripts/vm-lubuntu.sh`, la clé USB virtuelle et `vm-installe.sh` :

- les paquets de `scripts/apt-packages.txt` et `apt-packages-asus.txt` s'installent, puis `install-user.sh` et SigilDesk démarrent ;
- le plein écran masque le panneau LXQt, sans débordement (écran de 1368×768) ;
- `Ctrl+Alt+M` réduit SigilDesk, qui reste dans la barre des tâches ;
- une relance ramène la fenêtre existante, sans en ouvrir une deuxième ;
- PCManFM-Qt, LXImage-Qt, VLC, qpdfview et `lxqt-leave` sont présents d'origine, et les associations
  de fichiers (dossiers, JPEG, PNG, WEBP, MP4, PDF) pointent déjà vers eux ;
- Chromium est absent d'origine : les tuiles web passent par Firefox, le navigateur par défaut.

- après `install-system-deps.sh` (Chromium en snap), Facebook s'ouvre en fenêtre d'application,
  sans barre d'adresse, avec son propre nom dans la barre des tâches ;
- `qpdfview-translations` est déjà installé dans Lubuntu 26.04 : qpdfview n'est en anglais que
  dans une session anglaise (la session live).

- session repassée en français (`update-locale`, puis déconnexion et reconnexion) : avec
  l'autostart activé, SigilDesk s'ouvre seul à l'ouverture de la session LXQt ;
- extinction : après la confirmation de SigilDesk, `lxqt-leave --shutdown` affiche **sa propre
  confirmation** (« Voulez-vous vraiment éteindre votre ordinateur ? »). Cela fait deux
  confirmations à la suite, et le panneau LXQt réapparaît pendant la seconde. « Non » annule
  bien : SigilDesk revient au premier plan.

- une seule confirmation à l'extinction : celle de SigilDesk. La session éteint ensuite par D-Bus
  (`org.lxqt.session.powerOff`), sans la boîte de LXQt, et la VM s'est arrêtée jusqu'au bout ;
- mises à jour automatiques : apt suit `-security` et `-updates` ; les notificateurs de Lubuntu
  (`lubuntu-update-autostart`, Discover) sont masqués pour l'utilisateur. Avec `/run/reboot-required`
  simulé, le dialogue « Redémarrer pour terminer les mises à jour ? » apparaît seul, et « Plus tard »
  fonctionne ;
- restaurée depuis la barre des tâches après `Ctrl+Alt+M`, la fenêtre revenait en simple fenêtre
  maximisée, dock sous le panneau. C'est corrigé : elle repasse en plein écran ;
- au premier lancement, Chromium affiche une boîte « Conditions d'utilisation supplémentaires ». C'est
  à accepter une fois pendant la préparation de l'ASUS, pas par la personne.

Restent pour l'ASUS : pavé tactile réel, vitesse du N3060, Wi-Fi et batterie, extinction et
redémarrage réels sur l'installation (et non sur la session live).

## Critères non négociables

| Critère | Résultat | Preuve ou reste à faire |
|---|---|---|
| Capture exacte en 1366×768, grille 2 × 4, aucun débordement, dock et `SigilDesk · v1.0` visibles | **Testé** | `test_layout` : barre 24–70, salutation 105–195, grille 225–510 sur 628 px, dock 688–744, signature à 20 px du bord droit, aucun chevauchement, aucun libellé tronqué. Captures : `docs/captures/`. |
| Idem en mode confort, et à 1024×600 (standard et confort) | **Testé** | `test_layout`, 4 combinaisons, plus un fond sombre ; panneaux et dialogues dans l'écran dans les deux tailles. |
| Fond d'écran personnalisable et mémorisé, sans changer le bureau LXQt | **Testé** / à valider sur ASUS | `test_wallpapers` : JPEG, PNG et WEBP, image invalide, copie propre, original intact, persistance, repli si la copie disparaît. Le code n'écrit que dans `~/.local/share/sigildesk/`. À valider : import depuis une vraie clé USB avec le sélecteur de fichiers LXQt. |
| Mes favoris et mode confort utilisables sans apprentissage, réversibles, testés sur l'ASUS | **Testé** (fonctionnel) / **à valider sur ASUS** (ergonomie) | `test_favorites` (http(s), ajout, modification, suppression, ordre, persistance, limite de 12), `test_comfort` (tailles, bascule immédiate, persistance). À faire : la personne réelle, au pavé tactile. |
| Icônes de 60 à 64 px, lisibles, pavé tactile et clavier utilisables | **Testé** (tailles) / **à valider sur ASUS** (clavier et pavé) | 60 px en standard, 64 px en confort (`test_comfort`). La navigation au clavier (Tab, flèches, Entrée, Échap, anneau de focus) est codée et vérifiée à l'œil sur les captures, mais **non testée automatiquement**. |
| Aucun changement de session, GRUB, SDDM, permissions globales ou bureau LXQt | **Testé** | Aucun code n'écrit hors de `~/.config/sigildesk`, `~/.local/share/sigildesk`, `~/.local/state/sigildesk`, du lanceur, de l'entrée de menu, de l'icône et du fichier d'autostart. `test_scripts` vérifie que les fichiers LXQt, navigateur et autostart voisins restent intacts. |
| Pas de code PIN en dur, pas de faux contrôle de sécurité, privilèges par les mécanismes Linux existants | **Testé** (par conception) / **à valider sur ASUS** | Ni PIN ni verrou. Extinction par `lxqt-leave --shutdown` (session, puis logind), ou guide si indisponible (`test_maintenance`, `test_launcher`). À valider : comportement réel de `lxqt-leave` (double confirmation ou non). |
| Pas de promesse de vitesse ou de consommation sans mesure ; méthode fournie | **Testé** (méthode) / **à valider sur ASUS** (chiffres) | `scripts/measure.py` : délai, mémoire, processeur au repos. Repère du PC de développement seulement, aucun chiffre pour le N3060. |
| Pas d'accès root au lancement normal | **Testé** | L'application refuse l'UID 0 ; les scripts aussi (`refuse_root`) ; aucun `sudo` dans les scripts (`test_scripts`). |
| Installation et désinstallation réversibles, profil du navigateur jamais effacé | **Testé** | `test_scripts` : installation ×2, désinstallation ×2, autostart activé puis désactivé ×2, refus d'écraser un fichier étranger, `--purge` limité aux dossiers de SigilDesk, profil Chromium factice intact. |

## Fonctions

| Fonction | Résultat | Détail |
|---|---|---|
| 8 tuiles réelles (4 web, 4 locales), fixes | **Testé** | `test_launcher` : commandes construites, arguments séparés, sans shell. |
| Messagerie configurable, pas de Gmail par défaut | **Testé** | `test_config`, `test_launcher` ; pastille « À régler » et invitation au réglage. |
| Chromium préféré, navigateur du système en repli | **Testé** / à valider sur ASUS | Ordre de choix testé. À valider : Chromium (snap) au premier plan au-dessus du plein écran. |
| PCManFM-Qt, LXImage-Qt, VLC/mpv, qpdfview par les associations MIME | **Testé** (vérification) / **à valider sur ASUS** | `test_associations` ; *Paramètres › Applications* et `--doctor` signalent les écarts et proposent la commande `xdg-mime`, sans l'exécuter. Aucun de ces outils n'est installé dans le conteneur. |
| Date et heure locales, batterie, réseau | **Testé** (affichage) / à valider sur ASUS | Lecture de `/sys` ; valeurs réelles à vérifier sur la batterie de l'ASUS. |
| Fonds livrés, import, aperçu, Appliquer/Annuler, recadrage centré, réinitialisation | **Testé** | `test_wallpapers` ; captures `fond-ecran.png`, `accueil-fond-sombre.png`. |
| Lisibilité sur images contrastées | **Testé** (calcul) / à valider sur ASUS | Tonalité calculée sur le haut de l'image (claire ou sombre), voile dégradé, étiquettes sur pastilles, cartes opaques sur fond sombre. |
| Raccourci de maintenance `Ctrl+Alt+M`, conflit détecté | **Testé** (validation, conflits) / **à valider sur ASUS** | Lecture de `globalkeyshortcuts.conf` (LXQt). À valider : le raccourci agit bien sous le gestionnaire de fenêtres de Lubuntu. |
| Relance depuis LXQt, une seule instance | **Testé** / à valider sur ASUS | `test_single_instance` ; entrée de menu installée (`test_scripts`). |
| Autostart XDG, LXQt seulement | **Testé** (fichiers) / **validé sur ASUS** (session, 2026-11-01) | Posé par `install-user.sh` depuis le 2026-11-01 (demande d'Antoine ; `--sans-autostart` pour l'essai), `OnlyShowIn=LXQt`, `disable-autostart.sh` pour annuler. |
| Système utilisable si SigilDesk tombe | Par conception / **à valider sur ASUS** | Simple fenêtre ; aucun remplacement de session. Essai : `pkill` en cours d'utilisation. |
| Réglages JSON versionnés, validés, valeurs par défaut livrées, aucune donnée sensible | **Testé** | `test_config` : clés inconnues ou absentes, types, schéma futur jamais écrasé, fichier abîmé mis de côté. |
| README, guide utilisateur, guide de récupération, tests manuels | Fait | `README.md`, `docs/`. |
| Météo Open-Meteo : température, icône, conditions, ville, sous la date | **Testé** | `test_weather` (fournisseur, cache, service : erreurs réseau, ville inexistante, cache horodaté, désactivation sans aucune requête, réponse tardive ignorée), `test_layout` (aucun chevauchement à 1366×768 et 1024×600, en standard et en confort, ville longue et données de la veille). Météo réelle de Tours dans les captures. |
| Météo : actualisation toutes les 60 min, mode hors connexion, « Météo indisponible » | **Testé** | `test_weather` ; minuteries vérifiées (60 min, nouvel essai à 15 min). À valider sur ASUS : coupure Wi-Fi réelle. |
| Paramètres › Météo : activer, rechercher, choisir, changer de ville, sans géolocalisation | **Testé** | `test_weather` (recherche, choix, persistance), capture `meteo.png`. |
| Attribution Open-Meteo (CC BY 4.0), usage non commercial | Fait | Paramètres › Météo, À propos, README, LICENSE. |
| Icônes Wi-Fi (force du signal), Bluetooth, pile de batterie avec éclair de charge | **Testé** / à valider sur ASUS | `test_system_status` (faux /sys et /proc). À valider : vraie batterie et vrai Bluetooth de l'ASUS. |
| Noms sous les icônes (réglable) ; sans les noms, l'icône remplit la tuile | **Testé** | `test_comfort`, `test_layout` (icônes ≥ 80 px, dans la tuile). |
| Facebook, Mails, YouTube sans barre d'adresse | **Testé** (commande) / vu dans la VM | `test_launcher` (`--app=` avec Chromium seulement, Internet garde sa barre). |
| À propos : licence, créateur, site | Fait | Capture `a-propos.png` ; lien ouvert par le lanceur, adresse validée (`test_launcher`). |
| Mises à jour automatiques, sans intervention | **Testé** (réglage, VM) / **à valider sur ASUS** (passes réelles) | `install-system-deps.sh` : apt `-updates` et `-security`, `update-notifier-common`, notificateurs masqués (`test_scripts`). À valider : une passe nocturne réelle d'unattended-upgrades. |
| Dialogue de redémarrage si nécessaire | **Testé** | `test_updates` (`/run/reboot-required`, noyau plus récent, « Plus tard » : quatre heures) ; vu dans la VM. |
| Extinction et redémarrage en une seule confirmation | **Testé** | `test_maintenance` (D-Bus de la session, repli `lxqt-leave`, guide) ; extinction vue jusqu'au bout dans la VM. |
| Quatre premiers favoris en troisième rangée | **Testé** | `test_layout` (alignés sur les colonnes, sous les applications, au-dessus du dock, masqués à 1024×600 ou sans favori), `test_favorites` (ordre). |
| Retour aux fenêtres ouvertes (barre à part, tuiles qui ramènent leur fenêtre) | **Testé** / vu dans la VM | `test_windows` (relevé wmctrl réel de la VM, correspondances, activation), `test_layout` (barre séparée du dock, dans l'écran). Dans la VM : la tuile YouTube ramène la fenêtre ouverte, sans doublon. |
| Logo Sigilys system au démarrage, à l'arrêt et sur le bouton du menu | **Testé** (fichiers) / vu dans la VM (menu, thème par défaut) / **à valider sur ASUS** (démarrage réel) | `test_branding`. Dans la VM : le losange remplace l'oiseau sur le bouton du menu, `default.plymouth` pointe sur `sigilys`. Une session live ne reconstruit pas l'initramfs : le démarrage réel se voit sur l'ASUS. |
| Pas d'erreur d'économiseur d'écran au réveil (sans verrouilleur) | **Testé** / vu sur l'ASUS (réglage à la main) | `test_branding.SessionLockTests`, `test_scripts`. Sur l'ASUS, la case de LXQt décochée a supprimé l'erreur ; l'installation le fait désormais d'office. |
| Icône Wi-Fi à jour (au réveil notamment) | **Testé** (relevé toutes les 3 s) / **à valider sur ASUS** | Relevé passé de 30 s à 3 s (`test_system_status`). |
| Performances sur N3060 / 4 Go | **Non testé** | À mesurer avec `scripts/measure.py` sur l'ASUS. |
| Lecture MP4 720p fluide, PDF, clé USB | **Non testé** | Dépend de VLC/mpv, qpdfview et du matériel : [tests-manuels.md](tests-manuels.md). Depuis le 2026-11-01, `install-system-deps.sh` pose le pilote VA-API `i965-va-driver` (décodage H.264/HEVC par la puce) et `--doctor` / *Paramètres › Applications* disent si la puce décode (`infra/video_decoding.py`, `test_video_decoding`). |
