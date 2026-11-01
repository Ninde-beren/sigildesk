// Bouton radio large (hauteur theme.controlHeight), avec anneau de focus clavier.
import QtQuick
import QtQuick.Templates as T

T.RadioButton {
    id: control
    implicitHeight: theme.controlHeight
    implicitWidth: contentItem.implicitWidth + 4
    focusPolicy: Qt.StrongFocus
    hoverEnabled: true
    Accessible.name: text

    indicator: Rectangle {
        id: ring
        width: theme.comfort ? 28 : 24
        height: width
        x: 2
        anchors.verticalCenter: parent.verticalCenter
        radius: width / 2
        color: theme.surface
        border.width: theme.comfort ? 3 : 2
        border.color: control.checked ? theme.accent : "#7D8B99"
        Rectangle {
            anchors.centerIn: parent
            width: parent.width - 12
            height: width
            radius: width / 2
            color: theme.accent
            visible: control.checked
        }
        FocusRing { visible: control.visualFocus; baseRadius: parent.radius }
    }

    contentItem: Text {
        leftPadding: ring.width + 14
        verticalAlignment: Text.AlignVCenter
        text: control.text
        font.pixelSize: theme.fontBody
        font.weight: control.checked ? Font.DemiBold : Font.Normal
        color: theme.textColor
    }
}
