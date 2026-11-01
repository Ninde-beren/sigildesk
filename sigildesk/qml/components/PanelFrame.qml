// Cadre commun des panneaux : titre, bouton Fermer, contenu. Échap ferme.
import QtQuick
import QtQuick.Templates as T

T.Popup {
    id: panel
    property string title
    property int preferredWidth: 760
    property int preferredHeight: 560
    default property alias content: body.data
    property alias headerExtra: extra.data

    parent: T.Overlay.overlay
    anchors.centerIn: parent
    width: Math.min(preferredWidth, (parent ? parent.width : preferredWidth) - 32)
    height: Math.min(preferredHeight, (parent ? parent.height : preferredHeight) - 32)
    modal: true
    focus: true
    padding: 0
    closePolicy: T.Popup.CloseOnEscape

    T.Overlay.modal: Rectangle { color: Qt.rgba(0.08, 0.12, 0.17, 0.42) }

    background: Rectangle {
        objectName: panel.visible ? "geo_open_popup" : ""
        radius: 24
        color: theme.surface
        border.width: theme.comfort ? 2 : 1
        border.color: theme.borderColor
    }

    contentItem: Item {
        Item {
            id: header
            anchors { left: parent.left; right: parent.right; top: parent.top }
            height: theme.controlHeight + 28

            Text {
                anchors.left: parent.left
                anchors.leftMargin: 28
                anchors.right: extra.left
                anchors.rightMargin: 16
                anchors.verticalCenter: parent.verticalCenter
                text: panel.title
                elide: Text.ElideRight
                font.pixelSize: theme.fontPanelTitle
                font.weight: Font.DemiBold
                color: theme.textColor
            }
            Row {
                id: extra
                anchors.right: closeButton.left
                anchors.rightMargin: 12
                anchors.verticalCenter: parent.verticalCenter
                spacing: 10
            }
            SdButton {
                id: closeButton
                anchors.right: parent.right
                anchors.rightMargin: 20
                anchors.verticalCenter: parent.verticalCenter
                text: "Fermer"
                onClicked: panel.close()
            }
        }

        Rectangle {
            id: divider
            anchors { left: parent.left; right: parent.right; top: header.bottom }
            height: 1
            color: theme.borderColor
        }

        Item {
            id: body
            anchors { left: parent.left; right: parent.right; top: divider.bottom; bottom: parent.bottom }
            anchors.margins: 24
        }
    }
}
