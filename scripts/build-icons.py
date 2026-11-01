#!/usr/bin/env python3
"""Génère les icônes SVG de SigilDesk dans `sigildesk/resources/icons/`.

Pictogrammes maison : un carré arrondi en dégradé doux et un tracé blanc. Seules
exceptions, à la demande d'Antoine (2026-10-28) : Facebook et YouTube portent
leur logo reconnaissable, marques de Meta Platforms et de Google, employées
uniquement pour désigner leur service (voir LICENSE).
Pour personnaliser une icône sans toucher au code, déposer un fichier du même
nom dans `~/.local/share/sigildesk/icons/` (SVG ou PNG).

Usage : python3 scripts/build-icons.py
"""

from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "sigildesk" / "resources" / "icons"

# nom : (couleur haute, couleur basse, tracé dans un carré de 64)
TILES = {
    "internet": ("#7DBDF5", "#3B7BD6", '<circle cx="32" cy="32" r="14"/><ellipse cx="32" cy="32" rx="6.5" ry="14"/><path d="M18 32h28M20.5 24.5h23M20.5 39.5h23"/>'),
    "mail": ("#5BD6C3", "#1C9A8A", '<rect x="16.5" y="20.5" width="31" height="23" rx="4.5"/><path d="M18.5 23.5 32 33.5l13.5-10"/>'),
    "files": ("#FFD677", "#EFA238", '<path d="M16.5 24.5c0-2 1.6-3.5 3.5-3.5h7.5l3.5 4H44c2 0 3.5 1.6 3.5 3.5v12.5c0 2-1.6 3.5-3.5 3.5H20c-2 0-3.5-1.6-3.5-3.5z"/><path d="M16.5 29.5h31"/>'),
    "photos": ("#9BDDB4", "#46A673", '<rect x="16.5" y="18.5" width="31" height="27" rx="4.5"/><circle cx="38.5" cy="26.5" r="3.2"/><path d="M17.5 41.5l9-9.5 6.5 6.5 4-4 10 8.5"/>'),
    "videos": ("#BCAEF8", "#7861D9", '<rect x="17.5" y="17.5" width="29" height="29" rx="4.5"/><path d="M24 17.5v29M40 17.5v29M17.5 25.5H24M17.5 32H24M17.5 38.5H24M40 25.5h6.5M40 32h6.5M40 38.5h6.5"/>'),
    "fenetre": ("#AEBCCC", "#5F7387", '<rect x="15.5" y="18.5" width="33" height="27" rx="4.5"/><path d="M15.5 26.5h33"/><circle cx="21" cy="22.5" r=".6" fill="#fff"/><circle cx="25" cy="22.5" r=".6" fill="#fff"/>'),
    "pdf": ("#F493B1", "#C94A76", '<path d="M23 15.5h12.5l9 9V45c0 1.9-1.6 3.5-3.5 3.5H23c-1.9 0-3.5-1.6-3.5-3.5V19c0-1.9 1.6-3.5 3.5-3.5z"/><path d="M35.5 15.5v9h9"/><path d="M25.5 33h13M25.5 39h9"/>'),
}

FAVORITES = {
    "fav-etoile": ("#FFD677", "#EFA238", '<path d="M32 15.5l5.1 10.4 11.4 1.6-8.3 8 2 11.3L32 41.4l-10.2 5.4 2-11.3-8.3-8 11.4-1.6z"/>'),
    "fav-actualites": ("#93B6E3", "#4C74B5", '<rect x="16.5" y="18.5" width="26" height="27" rx="3.5"/><path d="M42.5 24.5h4.5v16.5c0 2.5-2 4.5-4.5 4.5"/><path d="M21.5 25h16M21.5 31h7M21.5 37.5h7M33 31h4.5v6.5H33z"/>'),
    "fav-meteo": ("#86CCF6", "#3D8FD8", '<circle cx="27" cy="27" r="5"/><path d="M27 17v2.5M17 27h2.5M20 20l1.8 1.8M34 20l-1.8 1.8"/><path d="M27 45h14a6 6 0 0 0 .4-12 8.2 8.2 0 0 0-15.6 3.2A4.4 4.4 0 0 0 27 45z"/>'),
    "fav-achats": ("#FFB582", "#EC7642", '<path d="M19.5 25h25l-2 19.3c-.2 1.8-1.7 3.2-3.5 3.2H25c-1.8 0-3.3-1.4-3.5-3.2z"/><path d="M26.5 29v-6a5.5 5.5 0 0 1 11 0v6"/>'),
    "fav-banque": ("#74D3AC", "#2B9A75", '<path d="M16.5 27 32 17.5 47.5 27z"/><path d="M21 31v10M28 31v10M36 31v10M43 31v10M16.5 45.5h31"/>'),
    "fav-sante": ("#F6A0AA", "#D85467", '<path d="M27 17.5h10v9.5h9.5v10H37v9.5H27V37h-9.5V27H27z"/>'),
    "fav-musique": ("#C6AAF6", "#8960D9", '<path d="M28.5 41V21l15-3.5V37"/><circle cx="24" cy="41" r="4.5"/><circle cx="39" cy="37" r="4.5"/>'),
    "fav-carte": ("#A0DA95", "#52A447", '<path d="M32 47.5S20.5 36.6 20.5 27.5a11.5 11.5 0 0 1 23 0c0 9.1-11.5 20-11.5 20z"/><circle cx="32" cy="27.5" r="4"/>'),
    "fav-cuisine": ("#FFC680", "#E5863A", '<path d="M23 16.5V27a4.5 4.5 0 0 0 9 0V16.5M27.5 16.5v31M41 16.5c-3.3 2.2-4.5 7.4-4.5 12.5H41v18.5"/>'),
    "fav-video": ("#FFA48F", "#E65E4D", '<circle cx="32" cy="32" r="14.5"/><path d="M29 26v12l9.5-6z" fill="#fff"/>'),
    "fav-jeux": ("#A5B4FF", "#5869DD", '<rect x="18.5" y="18.5" width="27" height="27" rx="6.5"/><g fill="#fff" stroke="none"><circle cx="25.5" cy="25.5" r="2.4"/><circle cx="38.5" cy="25.5" r="2.4"/><circle cx="32" cy="32" r="2.4"/><circle cx="25.5" cy="38.5" r="2.4"/><circle cx="38.5" cy="38.5" r="2.4"/></g>'),
    "fav-demarches": ("#AEBCCC", "#5F7387", '<path d="M23 15.5h18c1.9 0 3.5 1.6 3.5 3.5v26c0 1.9-1.6 3.5-3.5 3.5H23c-1.9 0-3.5-1.6-3.5-3.5V19c0-1.9 1.6-3.5 3.5-3.5z"/><path d="M25 25.5h14M25 31.5h8"/><path d="M27.5 40l3.2 3.2 6.3-6.4"/>'),
}

# Icônes du dock : tracé sombre sur fond clair, carré de 24.
DOCK = {
    "dock-favoris": '<path d="M12 3.6l2.55 5.2 5.7.82-4.12 4.03.97 5.67L12 16.64l-5.1 2.68.97-5.67-4.12-4.03 5.7-.82z"/>',
    "dock-parametres": '<path d="M4 7.5h9.5M18.5 7.5H20M4 16.5h1.5M10.5 16.5H20"/><circle cx="16" cy="7.5" r="2.5"/><circle cx="8" cy="16.5" r="2.5"/>',
    "dock-eteindre": '<path d="M12 3.5v8"/><path d="M7.1 6.6a7.6 7.6 0 1 0 9.8 0"/>',
}

# Logos de service (marques de leurs propriétaires), carré de 64, sans le fond maison.
BRANDS = {
    "facebook": '<circle cx="32" cy="32" r="30" fill="#0866FF"/>'
                '<path fill="#FFFFFF" d="M36.2 62V40.2h7.3l1.1-8.5h-8.4v-5.4c0-2.5.7-4.1 4.2-4.1h4.5v-7.6'
                'c-.8-.1-3.4-.3-6.5-.3-6.4 0-10.8 3.9-10.8 11.1v6.3h-7.3v8.5h7.3V62z"/>',
    "youtube": '<rect x="1" y="11" width="62" height="42" rx="12" fill="#FF0000"/>'
               '<path fill="#FFFFFF" d="M25.5 22v20l17-10z"/>',
}

# Bandeau d'état : tracé sombre sur pastille claire, carré de 24.
_ARC_BAS = '<path d="M9.2 15.3a4 4 0 0 1 5.6 0"/>'
_ARC_MILIEU = '<path d="M6.2 12.3a8.2 8.2 0 0 1 11.6 0"/>'
_ARC_HAUT = '<path d="M3.2 9.2a12.4 12.4 0 0 1 17.6 0"/>'
_POINT = '<circle cx="12" cy="18.6" r="1.5" fill="#1D2935" stroke="none"/>'


def _wifi(level: int) -> str:
    arcs = [_ARC_BAS, _ARC_MILIEU, _ARC_HAUT]
    return _POINT + "".join(arc if i < level else f'<g stroke-opacity=".28">{arc}</g>' for i, arc in enumerate(arcs))


STATUS = {
    "statut-wifi-1": _wifi(1),
    "statut-wifi-2": _wifi(2),
    "statut-wifi-3": _wifi(3),
    "statut-wifi-off": f'<g stroke-opacity=".35">{_POINT}{_ARC_BAS}{_ARC_MILIEU}{_ARC_HAUT}</g><path d="M4 4l16 16"/>',
    "statut-filaire": '<rect x="9" y="3.5" width="6" height="5" rx="1"/><rect x="3.5" y="15.5" width="6" height="5" rx="1"/>'
                      '<rect x="14.5" y="15.5" width="6" height="5" rx="1"/><path d="M12 8.5V12M6.5 15.5V12h11v3.5"/>',
    "statut-bluetooth": '<path d="M7 7.5l10 9-5 4.5v-18l5 4.5-10 9"/>',
    "statut-bluetooth-off": '<g stroke-opacity=".35"><path d="M7 7.5l10 9-5 4.5v-18l5 4.5-10 9"/></g><path d="M4 4l16 16"/>',
}

# Éclair de charge, posé sur la batterie dessinée en QML.
CHARGE = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24">\n'
    '  <!-- SigilDesk : icône « statut-charge » -->\n'
    '  <path d="M13.5 2 5 13.5h6L9.5 22 19 9.5h-6.5z" fill="#F5B83D" stroke="#1D2935" stroke-width="1.4" stroke-linejoin="round"/>\n'
    "</svg>\n"
)

# Météo : pictogrammes en couleur, sans fond, carré de 32 (posés sur une pastille claire).
_NUAGE = "M9 26h14.5a5.6 5.6 0 0 0 .7-11.15A8.2 8.2 0 0 0 8.4 16.6 4.7 4.7 0 0 0 9 26z"
_NUAGE_HAUT = "M9 21h14.5a5.6 5.6 0 0 0 .7-11.15A8.2 8.2 0 0 0 8.4 11.6 4.7 4.7 0 0 0 9 21z"


def _soleil(cx: float, cy: float, r: float, rays: float) -> str:
    lines = []
    for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0), (.707, .707), (-.707, .707), (.707, -.707), (-.707, -.707)):
        x1, y1 = cx + dx * (r + 2.2), cy + dy * (r + 2.2)
        x2, y2 = cx + dx * (r + 2.2 + rays), cy + dy * (r + 2.2 + rays)
        lines.append(f"M{x1:.1f} {y1:.1f}L{x2:.1f} {y2:.1f}")
    return (f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="#F5B83D"/>'
            f'<path d="{"".join(lines)}" stroke="#F5B83D" stroke-width="2.2" stroke-linecap="round"/>')


_LUNE = '<path d="M15 4.5a9.5 9.5 0 1 0 10.2 13.2A8 8 0 0 1 15 4.5z" fill="#8E9DCC"/>'
_PETITE_LUNE = '<path d="M11.5 3.5a7 7 0 1 0 7.5 9.7 5.9 5.9 0 0 1-7.5-9.7z" fill="#8E9DCC"/>'


def _nuage(path: str, fill: str = "#FFFFFF", stroke: str = "#7D93AA") -> str:
    return f'<path d="{path}" fill="{fill}" stroke="{stroke}" stroke-width="1.8" stroke-linejoin="round"/>'


WEATHER = {
    "meteo-soleil": _soleil(16, 16, 6.2, 3.4),
    "meteo-lune": _LUNE,
    "meteo-eclaircies": _soleil(11.5, 11.5, 4.6, 2.6) + _nuage("M12 27h12a5 5 0 0 0 .6-9.95A7 7 0 0 0 11.4 18.6 4.2 4.2 0 0 0 12 27z"),
    "meteo-eclaircies-nuit": _PETITE_LUNE + _nuage("M12 27h12a5 5 0 0 0 .6-9.95A7 7 0 0 0 11.4 18.6 4.2 4.2 0 0 0 12 27z"),
    "meteo-nuages": _nuage("M14 19h11a4.6 4.6 0 0 0 .5-9.15A6.6 6.6 0 0 0 13.4 11.4 3.8 3.8 0 0 0 14 19z", "#D5DDE6", "#8C9DB0")
                    + _nuage(_NUAGE),
    "meteo-brouillard": '<path d="M6 10h16M9 15h18M5 20h17M10 25h14" stroke="#8FA1B3" stroke-width="2.6" stroke-linecap="round"/>',
    "meteo-pluie": _nuage(_NUAGE_HAUT) + '<path d="M11 24l-1.6 4M16.5 24l-1.6 4M22 24l-1.6 4" stroke="#3D86D6" stroke-width="2.4" stroke-linecap="round"/>',
    "meteo-neige": _nuage(_NUAGE_HAUT) + "".join(
        f'<path d="M{x} 23v5M{x - 2.2} 24.25l4.4 2.5M{x - 2.2} 26.75l4.4-2.5" stroke="#6FA8DC" stroke-width="1.6" stroke-linecap="round"/>'
        for x in (10, 16, 22)),
    "meteo-orage": _nuage(_NUAGE_HAUT, "#C9D2DC", "#7D8B99") + '<path d="M17.5 17 12.5 24.5h4l-1.5 6 6-8.5h-4.2l1.7-5z" fill="#F5B83D" stroke="#B9831C" stroke-width="1" stroke-linejoin="round"/>',
    "meteo-indisponible": _nuage(_NUAGE, "none", "#9AA8B7") + '<path d="M6 6l20 20" stroke="#9AA8B7" stroke-width="2" stroke-linecap="round"/>',
}

APP_ICON = (
    "sigildesk",
    ("#B4CFEC", "#6C93C8"),
    '<g stroke="none"><rect x="17" y="17" width="13" height="13" rx="4" fill="#fff"/>'
    '<rect x="34" y="17" width="13" height="13" rx="4" fill="#fff" fill-opacity=".85"/>'
    '<rect x="17" y="34" width="13" height="13" rx="4" fill="#fff" fill-opacity=".85"/>'
    '<rect x="34" y="34" width="13" height="13" rx="4" fill="#DDF1E4"/></g>',
)


def tile_svg(name: str, top: str, bottom: str, glyph: str) -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64">\n'
        f'  <!-- SigilDesk : icône « {name} », générée par scripts/build-icons.py -->\n'
        f'  <defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{top}"/><stop offset="1" stop-color="{bottom}"/></linearGradient></defs>\n'
        '  <rect width="64" height="64" rx="18" fill="url(#g)"/>\n'
        '  <rect x=".5" y=".5" width="63" height="63" rx="17.5" fill="none" stroke="#fff" stroke-opacity=".25"/>\n'
        f'  <g fill="none" stroke="#fff" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round">{glyph}</g>\n'
        "</svg>\n"
    )


def dock_svg(name: str, glyph: str) -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24">\n'
        f'  <!-- SigilDesk : icône « {name} » -->\n'
        f'  <g fill="none" stroke="#1D2935" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">{glyph}</g>\n'
        "</svg>\n"
    )


def weather_svg(name: str, body: str) -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 32 32">\n'
        f'  <!-- SigilDesk : icône « {name} » -->\n'
        f"  {body}\n"
        "</svg>\n"
    )


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, (top, bottom, glyph) in {**TILES, **FAVORITES}.items():
        (OUT / f"{name}.svg").write_text(tile_svg(name, top, bottom, glyph), encoding="utf-8")
    for name, glyph in {**DOCK, **STATUS}.items():
        (OUT / f"{name}.svg").write_text(dock_svg(name, glyph), encoding="utf-8")
    (OUT / "statut-charge.svg").write_text(CHARGE, encoding="utf-8")
    for name, body in BRANDS.items():
        (OUT / f"{name}.svg").write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64">\n'
            f'  <!-- SigilDesk : logo « {name} », marque de son propriétaire -->\n  {body}\n</svg>\n', encoding="utf-8")
    for name, body in WEATHER.items():
        (OUT / f"{name}.svg").write_text(weather_svg(name, body), encoding="utf-8")
    name, (top, bottom), glyph = APP_ICON
    (OUT / f"{name}.svg").write_text(tile_svg(name, top, bottom, glyph), encoding="utf-8")
    total = len(TILES) + len(BRANDS) + len(FAVORITES) + len(DOCK) + len(STATUS) + 1 + len(WEATHER) + 1
    print(f"{total} icônes écrites dans {OUT}")


if __name__ == "__main__":
    main()
