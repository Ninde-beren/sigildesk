// Interrupteur large, avec « Activé » / « Désactivé » écrit en toutes lettres.
import QtQuick
import QtQuick.Templates as T

T.Switch {
    id: control
    implicitHeight: theme.controlHeight
    implicitWidth: track.width + 12 + stateLabel.implicitWidth
    focusPolicy: Qt.StrongFocus
    hoverEnabled: true
    Keys.onReturnPressed: { toggle(); toggled() }
    Keys.onEnterPressed: { toggle(); toggled() }

    indicator: Rectangle {
        id: track
        width: theme.comfort ? 68 : 58
        height: theme.comfort ? 36 : 32
        anchors.verticalCenter: parent.verticalCenter
        radius: height / 2
        color: control.checked ? theme.accent : "#B8C3CF"
        border.width: theme.comfort ? 2 : 0
        border.color: control.checked ? "#163E85" : "#7D8B99"

        Rectangle {
            x: control.checked ? parent.width - width - 4 : 4
            anchors.verticalCenter: parent.verticalCenter
            width: parent.height - 8
            height: width
            radius: width / 2
            color: "#FFFFFF"
        }
        FocusRing { visible: control.visualFocus; baseRadius: parent.radius }
    }

    contentItem: Text {
        id: stateLabel
        leftPadding: track.width + 12
        verticalAlignment: Text.AlignVCenter
        text: control.checked ? "Activé" : "Désactivé"
        font.pixelSize: theme.fontBody
        font.weight: Font.DemiBold
        color: theme.textColor
    }
}
