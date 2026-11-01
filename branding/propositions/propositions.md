# Sigilys system : trois propositions de logo

Proposées le 2026-10-28. Le logo remplace celui de Lubuntu à deux endroits : l'écran de démarrage et d'arrêt (Plymouth) et le bouton du menu du panneau LXQt (22 à 32 px sur `#2E3440`). La planche `planche.png` montre chaque direction à 22, 32, 64 et 200 px, en vraie grandeur, sur le panneau sombre et sur fond clair, en blanc monochrome, sur l'écran de démarrage, et dans un panneau simulé.

## Ce qu'il faut éviter

Sur ce créneau, les codes sont déjà pris : un symbole blanc dans un rond bleu (le colibri de Lubuntu), un anneau coupé par des points (Ubuntu), une lettre dans un cercle ou une bulle (elementary, Fedora), une spirale (Debian), l'orbe ou l'anneau multicolore qui se déforme (Siri, Copilot), l'étincelle ✦ de l'IA, le micro et l'onde sonore. Aucune des trois propositions n'emprunte ces formes.

## Positionnement commun

Un symbole géométrique et abstrait, calme et doux, qu'on prend au sérieux sans qu'il fasse « entreprise ». Le bleu brume, une couleur froide, est réchauffé par la crème. Deux couleurs au plus dans chaque symbole, sans filtre ni masque : le rendu est sûr avec QtSvg, donc avec LXQt et avec `scripts/build-branding.py`.

- **Fond de l'écran de démarrage : `#16202B`** (bleu nuit brumeux), la valeur par défaut de `build-branding.py`. Elle évite un flash clair entre l'écran noir de l'ASUS et la session.
- **Mot « Sigilys »** : dessiné au compas pour ces propositions, commun aux trois directions. Ses traits sont ronds et de même épaisseur, et les points des i sont de petits orbes. Il est en crème `#F4EFE5` et vectorisé en contours pleins, sans police à installer. Le bloc « symbole et nom » est vertical et fait 230 px de haut sur l'écran de démarrage, ce qui donne un symbole d'environ 160 px.

## A · Orbe (`a-orbe/`)

**Intention.** C'est l'orbe de Sigilys lui-même, réduit à sa forme la plus simple : une sphère dont la lumière vient du cœur, et l'anneau de l'interface, séparé d'elle par un vide. On reconnaît la même présence que sur le PC et la tablette.

**Couleurs.** Sphère en dégradé radial, de la crème `#F4EFE5` au cœur jusqu'à `#B4CFEC` puis `#6C93C8` au bord. Anneau `#6C93C8`. En blanc monochrome : un disque et un anneau.

**À 22 px.** Lisible : on voit un anneau et un point lumineux. La forme seule (deux cercles concentriques) reste commune : sans le dégradé, la version blanche ressemble à un bouton radio.

## B · Sceau (`b-sceau/`)

**Intention.** La tuile des icônes SigilDesk (même dégradé, même liseré) tournée d'un huitième de tour devient un sceau, avec l'orbe de Sigilys en son cœur. Le logo relie ainsi le bureau de la personne (SigilDesk) et l'assistant (Sigilys).

**Couleurs.** Losange en dégradé vertical de `#B4CFEC` à `#6C93C8`, liseré blanc à 25 %, halo crème à 35 %, orbe crème `#F4EFE5`. En blanc monochrome, l'orbe est détaché du losange par un vide, comme gravé.

**À 22 px.** C'est la plus nette des trois : la silhouette est franche, et elle se lit comme un bouton de la même famille que les icônes SigilDesk. Sur fond clair, la pointe du haut est plus pâle.

## C · Monogramme S (`c-monogramme-s/`)

**Intention.** L'initiale du système, tracée comme le voile de l'orbe : deux bras opposés autour d'un noyau. L'orbe est logé dans la jonction du S, qui s'écarte autour de lui.

**Couleurs.** Bras en dégradé léger, de `#B4CFEC` vers `#6C93C8`. Noyau crème bordé de `#B4CFEC`. En blanc monochrome, le dessin est le même, tout en blanc.

**À 22 px.** Encore lisible, mais c'est la plus fine des trois : la lettre est étroite, et le vide autour du noyau se ferme presque. Sur fond clair, le noyau disparaît. Dans le bloc de démarrage, le S répète l'initiale du mot écrit juste dessous.

## Recommandation

**B · Sceau.** C'est la seule des trois qui coche tout le cahier des charges sans réserve. Elle est la plus nette à 22 px, elle tient en blanc pur, et, à ma connaissance, aucune distribution courante n'utilise cette forme. Elle relie aussi SigilDesk et Sigilys en un seul signe, et une personne novice y reconnaît tout de suite un bouton de son bureau.

**En second : A · Orbe.** C'est la plus belle au démarrage et la plus fidèle à Sigilys. Sa forme est moins singulière une fois réduite au blanc.

Pour essayer une direction sans rien installer (avec `--sortie`, le résultat va dans un dossier jetable ; sans cette option, il remplace `branding/sigilys-system/`) :

```bash
.venv/bin/python scripts/build-branding.py --symbole branding/propositions/b-sceau/symbole.svg \
    --ecran branding/propositions/b-sceau/symbole-et-nom.svg --fond "#16202B" --accent "#B4CFEC" \
    --sortie /tmp/essai-sigilys
```

Ce rendu a été essayé hors cible pour les trois directions : le filigrane fait 169 × 230 px, et l'aperçu `apercu-demarrage.png` est correct. Il reste à le voir sur l'ASUS.
