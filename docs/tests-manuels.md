# Tests manuels sur l'ASUS E402SA

À faire dans une vraie session Lubuntu 26.04 / LXQt, au pavé tactile puis au
clavier. Cocher au fur et à mesure ; noter toute lenteur ou hésitation.

## Préparer les fichiers d'essai (une fois, sur une clé USB)

- `photo.jpg` : une photo de téléphone (JPEG, orientée en portrait si possible)
- `capture.png` : une image PNG
- `image.webp` : une image WEBP
- `video-720p.mp4` : une vidéo MP4 en 1280×720 (H.264 + AAC)
- `document.pdf` : un PDF de plusieurs pages

## Accueil

- [ ] Plein écran 1366×768 : date en haut, salutation et heure, 8 tuiles en 2 rangées, dock en bas, `SigilDesk · v1.0` en bas à droite. Rien ne déborde, rien ne défile.
- [ ] L'heure change à la minute.
- [ ] Batterie et Wi-Fi affichés en haut à droite, valeurs justes.
- [ ] Clavier : Tab parcourt tuiles puis dock ; flèches entre tuiles ; Entrée ouvre ; l'anneau bleu est bien visible.

## Préparation (par la personne qui installe, une fois)

- [ ] `scripts/install-system-deps.sh` puis `scripts/install-user.sh`.
- [ ] Ouvrir Chromium une fois, accepter ses conditions d'utilisation et fermer : la personne ne verra pas cette boîte.
- [ ] Choisir la messagerie et la ville de la météo dans les Paramètres.

## Tuiles web

- [ ] Internet, Facebook, YouTube s'ouvrent dans Chromium (ou le navigateur du système).
- [ ] Un double-clic impatient n'ouvre qu'une fenêtre ; le message « Ouverture… » s'affiche.
- [ ] Mails sans réglage : la pastille « À régler » est visible, un clic propose de choisir la messagerie.
- [ ] Paramètres › Messagerie : choisir le fournisseur, Enregistrer ; la tuile Mails ouvre le bon site.
- [ ] En fermant le navigateur, on retombe sur l'accueil.

## Tuiles locales et clé USB

- [ ] Fichiers ouvre PCManFM-Qt dans le dossier personnel.
- [ ] Photos ouvre le dossier Images avec des miniatures ; double-clic sur `photo.jpg` → LXImage-Qt.
- [ ] Vidéos ouvre le dossier Vidéos ; double-clic sur `video-720p.mp4` → VLC (ou mpv), image et son fluides en plein écran.
- [ ] PDF ouvre le dossier Documents ; double-clic sur `document.pdf` → qpdfview, pages lisibles, défilement correct.
- [ ] Clé USB branchée : visible dans PCManFM-Qt ; les fichiers s'y ouvrent comme ci-dessus.
- [ ] Paramètres › Applications › Vérifier : tout est coché, sinon appliquer la commande conseillée affichée.

## Fond d'écran

- [ ] Paramètres › Changer le fond d'écran : clic sur chaque image → aperçu immédiat ; Annuler revient au fond précédent.
- [ ] Appliquer, puis fermer et rouvrir SigilDesk : le fond est conservé.
- [ ] Importer `photo.jpg`, `capture.png` puis `image.webp` depuis la clé : aperçu correct, recadré sans déformation, photo dans le bon sens.
- [ ] Retirer la clé USB, rouvrir SigilDesk : le fond importé est toujours là.
- [ ] Importer un fichier qui n'est pas une image : message clair, rien ne casse.
- [ ] Textes lisibles sur chaque fond, y compris les fonds sombres.
- [ ] « Revenir au fond d'origine » remet « Aube solaire ».
- [ ] Le fond du bureau LXQt (SigilDesk réduit) n'a pas changé.

## Mes favoris

- [ ] Ouvrir Mes favoris ; un clic sur une carte ouvre le site.
- [ ] Ajouter : nom + adresse sans « https:// » (ex. `lemonde.fr`) + pictogramme → enregistré.
- [ ] Adresse invalide (`bonjour`, `javascript:…`) : message clair, rien n'est enregistré.
- [ ] Modifier la liste : Monter / Descendre / Modifier ; Retirer demande confirmation.
- [ ] Après redémarrage de SigilDesk, la liste et l'ordre sont conservés.
- [ ] À 12 favoris, « Ajouter » est grisé.

## Mode confort

- [ ] Activer : textes et tuiles grossissent immédiatement, la grille 2 × 4 et le dock restent visibles sans défilement.
- [ ] Tous les panneaux suivent (favoris, paramètres, fond d'écran, confirmations).
- [ ] Désactiver : retour à l'état standard ; réglage conservé après redémarrage.
- [ ] La résolution et l'échelle de LXQt n'ont pas changé.

## Maintenance, extinction, démarrage

- [ ] `Ctrl+Alt+M` réduit SigilDesk ; le bureau LXQt est accessible. Paramètres › Maintenance ne signale pas de conflit.
- [ ] Menu des applications › SigilDesk ramène la fenêtre existante (pas de deuxième fenêtre).
- [ ] Éteindre → une seule confirmation (celle de SigilDesk) → la session LXQt s'arrête proprement (applications fermées, pas de coupure brutale).
- [ ] `Ctrl+Alt+M`, puis clic sur SigilDesk dans la barre des tâches : retour en plein écran, dock visible.
- [ ] Mises à jour : le lendemain, *Paramètres › Maintenance* indique une passe automatique ; après une mise à jour du noyau, le dialogue « Redémarrer pour terminer les mises à jour ? » apparaît.
- [ ] Favoris : réordonner dans *Mes favoris*, la troisième rangée de l'accueil suit l'ordre.
- [ ] Après `install-user.sh`, nouvelle session : SigilDesk s'ouvre seul. `disable-autostart.sh` : il ne s'ouvre plus ; `enable-autostart.sh` : il s'ouvre de nouveau.
- [ ] `pkill -f 'python3 -m sigildesk'` pendant l'utilisation : le bureau LXQt reste utilisable.

## Mesures

```bash
free -m
python3 ~/.local/share/sigildesk/app/scripts/measure.py --duration 120
free -m
```

Noter : délai d'affichage, mémoire au repos, processeur au repos, et la
mémoire disponible avec Chromium ouvert sur YouTube.
