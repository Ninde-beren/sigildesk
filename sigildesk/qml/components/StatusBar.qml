// Barre du haut : la date à gauche, la météo juste dessous ; à droite Wi-Fi,
// Bluetooth et batterie. La météo déborde sous la barre, dans le coin haut-gauche
// que ni la salutation ni la grille n'occupent (vérifié par test_layout).
import QtQuick

Item {
    id: bar
    property color ink
    property color inkMuted
    property bool onDark: false
    property date now: new Date()
    signal weatherClicked()

    readonly property int pillHeight: theme.comfort ? 48 : 42
    readonly property int contentHeight: Math.max(dateText.implicitHeight, pillHeight)
    // Espace libre du bandeau, entre la date et les icônes d'état (barre des fenêtres ouvertes).
    readonly property real freeLeft: dateText.x + dateText.implicitWidth
    readonly property real freeRight: statusIcons.x

    function capitalize(text) { return text.length ? text.charAt(0).toUpperCase() + text.slice(1) : text }

    Timer {
        // Réveil une fois par minute, aligné sur le changement de minute.
        running: true
        repeat: true
        interval: 1000
        onTriggered: {
            bar.now = new Date()
            interval = (60 - bar.now.getSeconds()) * 1000 + 50
        }
    }

    Text {
        id: dateText
        objectName: "geo_date"
        anchors.left: parent.left
        anchors.leftMargin: 32
        anchors.verticalCenter: parent.verticalCenter
        text: bar.capitalize(bar.now.toLocaleDateString(Qt.locale("fr_FR"), "dddd d MMMM"))
        font.pixelSize: theme.fontBody + 3
        font.weight: Font.DemiBold
        color: bar.ink
    }

    WeatherWidget {
        objectName: "geo_weather"
        x: dateText.x - 8
        y: dateText.y + dateText.height + 6
        ink: bar.ink
        inkMuted: bar.inkMuted
        // Reste à gauche de la salutation, centrée, même à 1024×600 en mode confort.
        maxWidth: Math.min(theme.comfort ? 360 : 380, bar.width / 2 - 140)
        onClicked: bar.weatherClicked()
    }

    StatusIcons {
        id: statusIcons
        objectName: "geo_status_icons"
        anchors.right: parent.right
        anchors.rightMargin: 24
        anchors.verticalCenter: parent.verticalCenter
        height: bar.pillHeight
        onDark: bar.onDark
    }
}
