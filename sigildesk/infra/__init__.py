"""Couche d'accès au système : fichiers, processus, réseau, /sys, session LXQt.

Chaque module enveloppe une ressource extérieure derrière une petite API, avec
le point d'injection qui permet de la remplacer dans les tests (`which`,
`runner`, `starter`, `now`…) : `paths` (dossiers XDG), `config_store` (le fichier
de réglages), `processes` (programmes et lancements sans shell), `launcher`,
`xdg` (dossiers utilisateur, associations MIME), `lxqt` (raccourcis, extinction
par la session), `window_manager` (wmctrl), `system_probe` (/sys, /proc),
`updates`, `open_meteo` et `weather_cache`, `http_client`, `wallpaper_store`,
`single_instance`. Ces modules peuvent importer `domain`, jamais `ui`.
"""
