// Champ de saisie : grande hauteur, bordure bleue au focus, texte d'invite grisé.
import QtQuick
import QtQuick.Templates as T

T.TextField {
    id: control
    implicitHeight: theme.controlHeight
    implicitWidth: 320
    leftPadding: 16
    rightPadding: 16
    verticalAlignment: TextInput.AlignVCenter
    font.pixelSize: theme.fontBody
    color: theme.textColor
    selectionColor: "#2763C955"
    selectedTextColor: theme.textColor
    selectByMouse: true
    Accessible.name: placeholderText

    Text {
        x: control.leftPadding
        width: control.width - control.leftPadding - control.rightPadding
        height: control.height
        verticalAlignment: Text.AlignVCenter
        visible: control.text.length === 0 && control.preeditText.length === 0
        text: control.placeholderText
        elide: Text.ElideRight
        font: control.font
        color: theme.mutedColor
    }

    background: Rectangle {
        radius: 12
        color: theme.surfaceAlt
        border.width: control.activeFocus ? theme.focusWidth : (theme.comfort ? 2 : 1)
        border.color: control.activeFocus ? theme.focusColor : theme.borderColor
    }
}
