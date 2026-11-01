// Bloc de réglage : titre, explication en une phrase, puis la commande.
import QtQuick

Rectangle {
    id: card
    property string title
    property string description
    default property alias control: slot.data

    width: parent ? parent.width : 400
    height: column.height + 32
    radius: 16
    color: theme.surfaceAlt
    border.width: theme.comfort ? 2 : 0
    border.color: theme.borderColor

    Column {
        id: column
        x: 20
        y: 16
        width: card.width - 40
        spacing: 8
        Text {
            text: card.title
            font.pixelSize: theme.fontBody + 1
            font.weight: Font.DemiBold
            color: theme.textColor
        }
        Text {
            width: parent.width
            wrapMode: Text.WordWrap
            text: card.description
            font.pixelSize: theme.fontBody
            color: theme.mutedColor
        }
        Item {
            id: slot
            width: parent.width
            height: childrenRect.height
        }
    }
}
