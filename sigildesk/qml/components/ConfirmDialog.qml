// Demande de confirmation. Pour une action destructive, le focus part sur
// « Annuler » : Entrée par réflexe n'efface rien.
import QtQuick
import QtQuick.Templates as T

T.Popup {
    id: dialog
    property string title
    property string message
    property string confirmText: "Confirmer"
    property string cancelText: "Annuler"
    property bool destructive: false
    // Focus de départ sur « Annuler » : Entrée par réflexe ne déclenche rien.
    property bool focusCancel: destructive
    signal accepted()
    signal rejected()

    parent: T.Overlay.overlay
    anchors.centerIn: parent
    width: Math.min(600, (parent ? parent.width : 600) - 48)
    // Les Templates ne calculent pas de taille implicite : formule des styles Qt.
    implicitHeight: Math.max(implicitBackgroundHeight + topInset + bottomInset,
                             contentHeight + topPadding + bottomPadding)
    modal: true
    focus: true
    padding: 28
    closePolicy: T.Popup.CloseOnEscape

    onOpened: (focusCancel && cancelButton.visible ? cancelButton : confirmButton).forceActiveFocus(Qt.TabFocusReason)

    T.Overlay.modal: Rectangle { color: Qt.rgba(0.08, 0.12, 0.17, 0.45) }

    background: Rectangle {
        objectName: dialog.visible ? "geo_open_popup" : ""
        radius: 24
        color: theme.surface
        border.width: theme.comfort ? 2 : 1
        border.color: theme.borderColor
    }

    contentItem: Column {
        spacing: 18

        Text {
            width: parent.width
            text: dialog.title
            wrapMode: Text.WordWrap
            font.pixelSize: theme.fontPanelTitle
            font.weight: Font.DemiBold
            color: theme.textColor
        }
        Text {
            width: parent.width
            text: dialog.message
            wrapMode: Text.WordWrap
            lineHeight: 1.25
            font.pixelSize: theme.fontBody
            color: theme.mutedColor
        }
        Item {
            width: parent.width
            height: buttons.height + 6
            Row {
                id: buttons
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                spacing: 12
                SdButton {
                    id: cancelButton
                    visible: dialog.cancelText !== ""
                    text: dialog.cancelText
                    onClicked: { dialog.close(); dialog.rejected() }
                }
                SdButton {
                    id: confirmButton
                    kind: dialog.destructive ? "danger" : "primary"
                    text: dialog.confirmText
                    onClicked: { dialog.close(); dialog.accepted() }
                }
            }
        }
    }
}
