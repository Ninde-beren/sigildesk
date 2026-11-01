# Récupération : écran noir ou SigilDesk défaillant

SigilDesk est une fenêtre plein écran ordinaire posée sur LXQt. Il ne modifie
ni la session, ni LXQt, ni GRUB, ni SDDM. Le fermer suffit donc toujours à
retrouver le bureau, et le retirer ne laisse rien à restaurer côté LXQt.

## 1. SigilDesk est affiché mais bloque l'accès au bureau

Dans l'ordre, jusqu'à ce que le bureau LXQt réapparaisse :

1. `Ctrl+Alt+M` : réduit SigilDesk (raccourci de maintenance).
2. `Alt+F4` : ferme la fenêtre (géré par le gestionnaire de fenêtres).
3. *Paramètres* › *Maintenance* › *Quitter SigilDesk*.
4. Un terminal (`Ctrl+Alt+T` sous Lubuntu, ou menu › Outils système › QTerminal), puis :

```bash
pkill -f 'python3 -m sigildesk'
```

Pour revenir ensuite : menu des applications › Accessoires › SigilDesk.

## 2. Écran noir au lieu de l'accueil

L'affichage accéléré de la puce graphique peut échouer. Essayer le rendu logiciel :

```bash
pkill -f 'python3 -m sigildesk'
~/.local/bin/sigildesk --software
```

Si cela règle le problème, le dire à la personne qui maintient l'ordinateur : il
faudra ajouter `--software` au lanceur.

## 3. Écran noir dès l'ouverture de session

Couper l'ouverture automatique depuis une console texte :

1. `Ctrl+Alt+F3` : console texte. Se connecter avec le même compte.
2. Désactiver l'autostart de SigilDesk, puis redémarrer :

```bash
rm -f ~/.config/autostart/sigildesk.desktop
systemctl reboot
```

La session LXQt revient alors telle qu'avant SigilDesk. Si l'écran reste noir
sans SigilDesk, le problème vient d'ailleurs (pilote, LXQt) : SigilDesk n'y est
pour rien et n'a rien modifié.

## 4. Réglages abîmés

SigilDesk met de côté un fichier de réglages illisible
(`~/.config/sigildesk/config.invalide-<date>.json`) et repart des réglages par
défaut. Pour repartir de zéro à la main :

```bash
mv ~/.config/sigildesk/config.json ~/.config/sigildesk/config.json.ancien
```

## 5. Mise en veille

Si l'écran doit être verrouillé au réveil (avec mot de passe), installer un
écran de verrouillage, puis rétablir le réglage de LXQt :

```bash
sudo apt install xscreensaver
python3 ~/.local/share/sigildesk/app/scripts/session-lock.py retablir
```

## 6. Mises à jour

Elles s'installent seules. Pour revenir au comportement d'origine de Lubuntu
(mises à jour de sécurité seules, notificateurs rétablis) :

```bash
~/.local/share/sigildesk/app/scripts/disable-auto-updates.sh
```

## 7. Tout retirer

```bash
~/.local/share/sigildesk/app/scripts/disable-autostart.sh
~/.local/share/sigildesk/app/scripts/uninstall-user.sh
```

`uninstall-user.sh --purge` efface aussi les réglages, favoris et fonds
importés, après confirmation. Le navigateur, ses favoris et son profil, ainsi
que les documents, ne sont jamais touchés.

## Où regarder

- Journal : `~/.local/state/sigildesk/sigildesk.log`
- Diagnostic : `~/.local/share/sigildesk/app/scripts/check-deps.sh`
