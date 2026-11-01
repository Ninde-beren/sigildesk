// Fenêtre principale de SigilDesk : accueil, dock et panneaux.
// Objets fournis par Python (sigildesk/app.py, couche ui/) : app (contrôleur),
// theme, favorites, wallpapers, webTiles, localTiles, systemStatus, weather,
// updates, openWindows, icons, et les entiers initialWidth, initialHeight.
// Le QML affiche et appelle ; il ne décide de rien (voir docs/architecture.md).
import QtQuick
import QtQuick.Window
import "components"

Window {
    id: root
    width: initialWidth
    height: initialHeight
    minimumWidth: 800
    minimumHeight: 560
    visible: false
    title: "SigilDesk"
    color: "#DCE6EE"

    readonly property bool onDark: wallpapers.tone === "dark"
    readonly property color ink: onDark ? "#F5F8FB" : theme.textColor
    readonly property color inkMuted: onDark ? "#DCE5EE" : theme.mutedColor
    readonly property bool imagesReady: background.ready

    // Mise en page verticale. À 1366×768 en mode standard elle donne :
    // barre 24–70, salutation 105–195, grille 241–493 (centrée dans la bande
    // 225–510 de la maquette), dock 688–744.
    // Plus bas (1024×600), les marges se resserrent ; rien ne défile.
    readonly property bool compact: height < 700
    readonly property int marginV: compact ? 12 : 24
    readonly property int statusH: Math.max(compact ? 40 : 46, statusBar.contentHeight)
    readonly property int fixedV: 2 * marginV + statusH + greeting.height + theme.dockHeight
    readonly property int twoRowsH: 2 * theme.tileHeight + theme.tileGap
    // Troisième rangée (4 premiers favoris) seulement si elle tient avec de l'air :
    // oui à 1366×768 (standard et confort), non à 1024×600.
    readonly property bool favoritesRow: favorites.count > 0
        && height - fixedV - twoRowsH - theme.tileHeight - theme.tileGap >= 60
    readonly property int freeV: Math.max(0, height - fixedV - tileGrid.height)
    // Salutation au plus à 35 px sous la barre (105–195 à 1366×768), grille au plus 46 px dessous.
    readonly property int gapTop: Math.round(Math.min(freeV * 0.3, 35))
    readonly property int gapMid: Math.round(Math.min((freeV - gapTop) * 0.35, 46))

    Background {
        id: background
        anchors.fill: parent
        source: wallpapers.source
        dark: root.onDark
        strongVeil: theme.comfort
    }

    StatusBar {
        id: statusBar
        objectName: "geo_status"
        x: 0
        y: root.marginV
        width: parent.width
        height: root.statusH
        ink: root.ink
        inkMuted: root.inkMuted
        onDark: root.onDark
        onWeatherClicked: settingsPanel.openSectionNamed("meteo")
    }

    Greeting {
        id: greeting
        objectName: "geo_greeting"
        anchors.horizontalCenter: parent.horizontalCenter
        y: statusBar.y + statusBar.height + root.gapTop
        compact: root.compact
        ink: root.ink
        userName: app.userName
    }

    TileGrid {
        id: tileGrid
        objectName: "geo_grid"
        anchors.horizontalCenter: parent.horizontalCenter
        y: greeting.y + greeting.height + root.gapMid
        showFavorites: root.favoritesRow
        onDark: root.onDark
        ink: root.ink
    }

    Dock {
        id: dock
        objectName: "geo_dock"
        anchors.horizontalCenter: parent.horizontalCenter
        y: parent.height - root.marginV - height
        onFavorites: favoritesPanel.open()
        onSettings: settingsPanel.openSectionNamed("affichage")
        onPower: root.askPowerOff()
    }

    OpenWindowsBar {
        objectName: "geo_windows_bar"
        anchors.horizontalCenter: parent.horizontalCenter
        height: statusBar.pillHeight
        y: statusBar.y + (statusBar.height - height) / 2
        // Centrée dans le bandeau, sans toucher la date ni les icônes d'état.
        maxWidth: 2 * Math.min(root.width / 2 - statusBar.freeLeft - 24, statusBar.freeRight - root.width / 2 - 24)
        onDark: root.onDark
        onMore: windowsPanel.open()
    }

    Text {
        objectName: "geo_signature"
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.rightMargin: 20
        anchors.bottomMargin: root.compact ? 8 : 12
        text: "SigilDesk · v" + app.version
        font.pixelSize: theme.signatureSize
        color: root.inkMuted
        opacity: 0.85
        Accessible.ignored: true
    }

    Toast {
        id: toast
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: dock.top
        anchors.bottomMargin: 16
    }

    // --- Panneaux et dialogues ------------------------------------------------

    FavoritesPanel {
        id: favoritesPanel
        onEditRequested: function(row) { favoriteEditor.openFor(row) }
        onRemoveRequested: function(row) {
            removeConfirm.row = row
            removeConfirm.title = "Retirer « " + favorites.get(row).name + " » ?"
            removeConfirm.open()
        }
    }

    FavoriteEditor { id: favoriteEditor }

    WindowsPanel { id: windowsPanel }

    ConfirmDialog {
        id: removeConfirm
        property int row: -1
        message: "Ce lien sera retiré de vos favoris. Le site lui-même n'est pas touché."
        confirmText: "Retirer"
        destructive: true
        onAccepted: favorites.remove(row)
    }

    SettingsPanel {
        id: settingsPanel
        onWallpaperRequested: { settingsPanel.close(); wallpaperSheet.open() }
        onMinimizeRequested: { settingsPanel.close(); app.minimize() }
        onQuitRequested: quitConfirm.open()
    }

    WallpaperSheet { id: wallpaperSheet }

    ConfirmDialog {
        id: quitConfirm
        title: "Quitter SigilDesk ?"
        message: "Le bureau LXQt reste disponible. Pour revenir, ouvrez SigilDesk depuis le menu des applications."
        confirmText: "Quitter"
        destructive: true
        onAccepted: app.quit()
    }

    ConfirmDialog {
        id: powerConfirm
        title: "Éteindre l'ordinateur ?"
        message: "Pensez à enregistrer vos documents ouverts. L'ordinateur va s'éteindre."
        confirmText: "Éteindre"
        destructive: true
        onAccepted: app.powerOff()
    }

    ConfirmDialog {
        id: powerGuide
        title: "Pour éteindre l'ordinateur"
        message: "1. Cliquez sur « Afficher le bureau » ci-dessous.\n"
               + "2. Ouvrez le menu en bas à gauche de l'écran.\n"
               + "3. Choisissez « Quitter », puis « Éteindre »."
        confirmText: "Afficher le bureau"
        cancelText: "Fermer"
        onAccepted: app.minimize()
    }

    ConfirmDialog {
        // Proposé par le moniteur de mises à jour ; « Plus tard » repose la question dans 4 h.
        id: rebootDialog
        title: "Redémarrer pour terminer les mises à jour ?"
        message: "L'ordinateur s'est mis à jour tout seul. Pour terminer, il doit redémarrer.\n"
               + "Pensez à enregistrer vos documents ouverts."
        confirmText: "Redémarrer maintenant"
        cancelText: "Plus tard"
        focusCancel: true  // le dialogue arrive seul : jamais de redémarrage sur un Entrée réflexe
        onAccepted: app.reboot()
        onRejected: updates.later()
    }

    ConfirmDialog {
        id: mailSetup
        title: "Votre messagerie n'est pas encore choisie"
        message: "Indiquez une fois pour toutes le site de votre messagerie (Gmail, Orange, Free…). Le bouton Mails l'ouvrira ensuite directement."
        confirmText: "Choisir ma messagerie"
        cancelText: "Plus tard"
        onAccepted: settingsPanel.openSectionNamed("messagerie")
    }

    // --- Comportements ----------------------------------------------------------

    function askPowerOff() {
        if (app.canPowerOff)
            powerConfirm.open()
        else
            powerGuide.open()
    }

    function closePanels() {
        for (const popup of [favoritesPanel, favoriteEditor, removeConfirm, settingsPanel, wallpaperSheet,
                             quitConfirm, powerConfirm, powerGuide, mailSetup, rebootDialog, windowsPanel])
            popup.close()
    }

    // Restaurée depuis la barre des tâches après Ctrl+Alt+M, la fenêtre revient
    // « normale » ou « maximisée » (constaté sous Lubuntu 26.04) : on repasse en
    // plein écran, sinon le dock finit sous le panneau LXQt.
    onVisibilityChanged: function(visibility) {
        if (app.startFullScreen && (visibility === Window.Windowed || visibility === Window.Maximized))
            Qt.callLater(root.showFullScreen)
    }

    // Fenêtres ouvertes : relevées seulement quand l'accueil est au premier plan.
    onActiveChanged: openWindows.setWatching(root.active)

    function restore() {
        if (app.startFullScreen)
            root.showFullScreen()
        else
            root.showNormal()
        root.raise()
        root.requestActivate()
    }

    Shortcut {
        // Maintenance : laisse la place au bureau LXQt.
        sequence: app.maintenanceShortcut
        context: Qt.ApplicationShortcut
        onActivated: { root.closePanels(); app.minimize() }
    }

    Connections {
        target: app
        function onToast(message) { toast.show(message) }
        function onMailSetupRequested() { mailSetup.open() }
        function onPowerGuideRequested() { powerGuide.open() }
        function onMinimizeRequested() { root.showMinimized() }
        function onActivateRequested() { root.restore() }
        function onPanelRequested(name) {
            if (name === "favoris") favoritesPanel.open()
            else if (name === "parametres") settingsPanel.openSectionNamed("affichage")
            else if (name === "fonds") wallpaperSheet.open()
            else if (name === "eteindre") root.askPowerOff()
            else if (name === "editeur") favoriteEditor.openFor(-1)
            else if (name === "dossiers") settingsPanel.openSectionNamed("dossiers")
            else if (name === "meteo") settingsPanel.openSectionNamed("meteo")
            else if (name === "apropos") settingsPanel.openSectionNamed("apropos")
            else if (name === "redemarrer") rebootDialog.open()
            else if (name === "maintenance") settingsPanel.openSectionNamed("maintenance")
        }
    }

    Connections {
        target: updates
        function onRebootSuggested() {
            if (!rebootDialog.opened && !powerConfirm.opened)
                rebootDialog.open()
        }
    }

    Connections {
        target: wallpapers
        function onMessage(text) { toast.show(text) }
    }

    Component.onCompleted: {
        if (app.startFullScreen)
            root.showFullScreen()
        else
            root.show()
        tileGrid.focusFirst()
    }
}
