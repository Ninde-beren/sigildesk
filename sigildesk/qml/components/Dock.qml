// Dock compact en bas de l'écran : favoris, paramètres, extinction.
// Les fenêtres ouvertes ont leur propre barre (OpenWindowsBar), à part.
import QtQuick

Item {
    id: dock
    signal favorites()
    signal settings()
    signal power()

    height: theme.dockHeight
    width: row.implicitWidth + 16

    Rectangle {
        anchors.fill: parent
        anchors.topMargin: 4
        anchors.bottomMargin: -4
        radius: height / 2
        color: "#14263A"
        opacity: 0.12
    }
    Rectangle {
        anchors.fill: parent
        radius: height / 2
        color: Qt.rgba(1, 1, 1, wallpapers.tone === "dark" ? 0.96 : theme.cardOpacity)
        border.width: theme.comfort ? 2 : 1
        border.color: theme.borderColor
    }

    Row {
        id: row
        anchors.centerIn: parent
        spacing: 4

        DockButton {
            objectName: "geo_dock_favoris"
            iconName: "dock-favoris"
            text: "Mes favoris"
            onClicked: dock.favorites()
        }
        DockButton {
            objectName: "geo_dock_parametres"
            iconName: "dock-parametres"
            text: "Paramètres"
            onClicked: dock.settings()
        }
        DockButton {
            objectName: "geo_dock_eteindre"
            iconName: "dock-eteindre"
            text: "Éteindre"
            onClicked: dock.power()
        }
    }
}
