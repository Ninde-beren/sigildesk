// Ajout ou modification d'un favori : nom, adresse http(s) vérifiée, pictogramme.
import QtQuick
import QtQuick.Templates as T

PanelFrame {
    id: editor
    property int row: -1
    property string chosenIcon: "fav-etoile"
    property string error: ""
    property bool touched: false

    title: row < 0 ? "Ajouter un favori" : "Modifier le favori"
    preferredWidth: 660
    preferredHeight: theme.comfort ? 640 : 580

    readonly property var iconChoices: [
        "fav-etoile", "fav-actualites", "fav-meteo", "fav-achats", "fav-banque", "fav-sante",
        "fav-musique", "fav-carte", "fav-cuisine", "fav-video", "fav-jeux", "fav-demarches"
    ]

    function openFor(index) {
        row = index
        const item = index >= 0 ? favorites.get(index) : ({})
        nameField.text = item.name || ""
        urlField.text = item.url || ""
        chosenIcon = item.icon || "fav-etoile"
        error = ""
        touched = false
        open()
        nameField.forceActiveFocus()
    }

    function save() {
        touched = true
        const message = row < 0
            ? favorites.add(nameField.text, urlField.text, chosenIcon)
            : favorites.update(row, nameField.text, urlField.text, chosenIcon)
        error = message
        if (message === "")
            close()
    }

    Flickable {
        id: scroller
        anchors.fill: parent
        anchors.rightMargin: 14
        clip: true
        contentHeight: form.height
        boundsBehavior: Flickable.StopAtBounds

        Column {
            id: form
            width: parent.width
            spacing: 10

            Text { text: "Nom"; font.pixelSize: theme.fontBody; font.weight: Font.DemiBold; color: theme.textColor }
            SdTextField {
                id: nameField
                width: parent.width
                placeholderText: "exemple : Météo"
                maximumLength: 32
                onTextEdited: if (editor.touched) editor.error = favorites.check(nameField.text, urlField.text)
            }
            Item { width: 1; height: 4 }
            Text { text: "Adresse du site"; font.pixelSize: theme.fontBody; font.weight: Font.DemiBold; color: theme.textColor }
            SdTextField {
                id: urlField
                width: parent.width
                placeholderText: "exemple : meteofrance.com"
                inputMethodHints: Qt.ImhUrlCharactersOnly | Qt.ImhNoAutoUppercase
                onTextEdited: if (editor.touched) editor.error = favorites.check(nameField.text, urlField.text)
                onAccepted: editor.save()
            }
            Text {
                width: parent.width
                height: Math.max(implicitHeight, theme.fontBody + 8)
                text: editor.error
                wrapMode: Text.WordWrap
                font.pixelSize: theme.fontBody
                font.weight: Font.DemiBold
                color: theme.danger
                Accessible.role: Accessible.AlertMessage
            }
            Text { text: "Pictogramme"; font.pixelSize: theme.fontBody; font.weight: Font.DemiBold; color: theme.textColor }
            Grid {
                columns: 6
                spacing: 12
                Repeater {
                    model: editor.iconChoices
                    delegate: T.AbstractButton {
                        id: choice
                        required property string modelData
                        width: theme.comfort ? 60 : 54
                        height: width
                        focusPolicy: Qt.StrongFocus
                        checkable: true
                        checked: editor.chosenIcon === modelData
                        Accessible.name: "Pictogramme " + modelData.replace("fav-", "")
                        onClicked: editor.chosenIcon = modelData
                        Keys.onReturnPressed: clicked()
                        background: Rectangle {
                            radius: 16
                            color: choice.checked ? "#DCE7F7" : "transparent"
                            border.width: choice.checked ? theme.focusWidth : 0
                            border.color: theme.accent
                            FocusRing { visible: choice.visualFocus; baseRadius: 16 }
                        }
                        contentItem: Item {
                            Icon { anchors.centerIn: parent; name: choice.modelData; size: choice.width - 12 }
                        }
                    }
                }
            }
            Item { width: 1; height: 8 }
            Row {
                anchors.right: parent.right
                spacing: 12
                SdButton { text: "Annuler"; onClicked: editor.close() }
                SdButton { objectName: "geo_fav_save"; kind: "primary"; text: "Enregistrer"; onClicked: editor.save() }
            }
        }
    }
    ScrollHint { flick: scroller }
}
