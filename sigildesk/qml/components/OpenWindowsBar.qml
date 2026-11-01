// Fenêtres restées ouvertes (YouTube, un dossier, une vidéo…), en haut au centre
// du bandeau, à part du dock : en plein écran, SigilDesk cache la barre des
// tâches de LXQt, et c'est par ici qu'on y revient d'un clic. Masquée s'il n'y a
// rien d'ouvert.
import QtQuick

Item {
    id: bar
    signal more()

    property int maxWidth: 400
    property bool onDark: false
    readonly property int chipText: theme.comfort ? 118 : 104
    readonly property int chipWidth: chipText + (theme.comfort ? 26 : 24) + 46
    readonly property int moreWidth: theme.comfort ? 186 : 166
    readonly property int space: Math.max(0, maxWidth - 16)
    readonly property int chipCount: openWindows.count * (chipWidth + 4) <= space ? openWindows.count
        : Math.max(0, Math.floor((space - moreWidth) / (chipWidth + 4)))
    readonly property bool overflow: openWindows.count > chipCount

    visible: openWindows.count > 0 && maxWidth >= moreWidth + 16
    width: row.implicitWidth + 16

    Rectangle {
        // Même style que la pastille d'état, juste à côté.
        anchors.fill: parent
        radius: height / 2
        color: Qt.rgba(1, 1, 1, bar.onDark || theme.comfort ? 0.92 : 0.74)
        border.width: theme.comfort ? 2 : 1
        border.color: theme.borderColor
    }

    Row {
        id: row
        anchors.centerIn: parent
        spacing: 4

        Repeater {
            model: openWindows
            delegate: DockButton {
                required property int index
                required property string windowId
                required property string label
                required property string windowIcon
                required property string title
                objectName: "geo_window_" + index
                visible: index < bar.chipCount
                height: bar.height - 6
                iconName: windowIcon
                text: label
                maxTextWidth: bar.chipText
                Accessible.name: "Revenir à " + label
                Accessible.description: title
                onClicked: openWindows.activate(windowId)
            }
        }

        DockButton {
            objectName: "geo_window_more"
            visible: bar.overflow
            height: bar.height - 6
            iconName: "fenetre"
            text: (bar.chipCount === 0 ? "Fenêtres (" : "Autres (") + (openWindows.count - bar.chipCount) + ")"
            maxTextWidth: bar.moreWidth - (theme.comfort ? 26 : 24) - 46
            Accessible.name: bar.chipCount === 0 ? "Fenêtres ouvertes" : "Autres fenêtres ouvertes"
            onClicked: bar.more()
        }
    }
}
