// Bouton du dock : icône et texte court sur une pastille, texte raccourci si la place manque.
import QtQuick
import QtQuick.Templates as T

T.AbstractButton {
    id: button
    property string iconName
    property int maxTextWidth: 0  // 0 : pas de limite ; sinon le texte est raccourci

    implicitHeight: theme.dockHeight - 12
    implicitWidth: content.implicitWidth + 36
    focusPolicy: Qt.StrongFocus
    hoverEnabled: true
    Accessible.name: text
    Keys.onReturnPressed: clicked()
    Keys.onEnterPressed: clicked()

    background: Rectangle {
        radius: height / 2
        color: button.down ? theme.pressed : button.hovered ? theme.surfaceAlt : "transparent"
        FocusRing { visible: button.visualFocus; baseRadius: parent.radius }
    }

    contentItem: Item {
        implicitWidth: content.implicitWidth
        Row {
            id: content
            anchors.centerIn: parent
            spacing: 10
            Icon {
                anchors.verticalCenter: parent.verticalCenter
                name: button.iconName
                size: theme.comfort ? 26 : 24
            }
            Text {
                anchors.verticalCenter: parent.verticalCenter
                width: button.maxTextWidth > 0 ? Math.min(implicitWidth, button.maxTextWidth) : implicitWidth
                elide: Text.ElideRight
                text: button.text
                font.pixelSize: theme.fontBody
                font.weight: Font.DemiBold
                color: theme.textColor
            }
        }
    }
}
