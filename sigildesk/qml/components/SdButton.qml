// Bouton texte : « primary » (bleu), « danger » (rouge) ou « secondary » (clair).
import QtQuick
import QtQuick.Templates as T

T.Button {
    id: control
    property string kind: "secondary"

    implicitHeight: theme.controlHeight
    implicitWidth: Math.max(theme.controlHeight, label.implicitWidth + leftPadding + rightPadding)
    leftPadding: 20
    rightPadding: 20
    focusPolicy: Qt.StrongFocus
    hoverEnabled: true
    Accessible.name: text
    Keys.onReturnPressed: clicked()
    Keys.onEnterPressed: clicked()

    readonly property color fill: kind === "primary" ? theme.accent : kind === "danger" ? theme.danger : theme.surfaceAlt

    background: Rectangle {
        radius: height / 2
        color: control.down ? Qt.darker(control.fill, 1.15) : control.hovered ? Qt.darker(control.fill, 1.06) : control.fill
        border.width: control.kind === "secondary" ? (theme.comfort ? 2 : 1) : 0
        border.color: theme.borderColor
        opacity: control.enabled ? 1 : 0.45
        FocusRing { visible: control.visualFocus; baseRadius: parent.radius }
    }

    contentItem: Text {
        id: label
        text: control.text
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
        font.pixelSize: theme.fontBody
        font.weight: Font.DemiBold
        color: control.kind === "secondary" ? theme.textColor : "#FFFFFF"
        opacity: control.enabled ? 1 : 0.6
    }
}
