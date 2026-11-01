// Anneau de focus clavier : bleu franc doublé d'un liseré blanc, visible sur tout fond.
import QtQuick

Rectangle {
    property real baseRadius: 12
    readonly property int gap: 3

    anchors.fill: parent
    anchors.margins: -(gap + theme.focusWidth)
    radius: baseRadius + gap + theme.focusWidth
    color: "transparent"
    border.width: theme.focusWidth
    border.color: theme.focusColor

    Rectangle {
        anchors.fill: parent
        anchors.margins: -2
        radius: parent.radius + 2
        color: "transparent"
        border.width: 2
        border.color: "#FFFFFF"
    }
}
