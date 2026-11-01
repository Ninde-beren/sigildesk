// Choix du fond d'écran, en bas de l'écran pour garder l'accueil visible :
// un clic essaie l'image, « Appliquer » la garde, « Annuler » revient en arrière.
import QtQuick
import QtQuick.Templates as T
import QtQuick.Dialogs

T.Popup {
    id: sheet
    property string error: ""
    property bool applied: false

    parent: T.Overlay.overlay
    x: 24
    y: (parent ? parent.height : 768) - height - 16
    width: (parent ? parent.width : 1366) - 48
    height: column.implicitHeight + 40
    modal: true
    focus: true
    padding: 20
    closePolicy: T.Popup.CloseOnEscape

    // Bloque les clics sur l'accueil sans l'assombrir : l'aperçu reste fidèle.
    T.Overlay.modal: Rectangle { color: "transparent" }

    onOpened: { error = ""; applied = false; list.forceActiveFocus() }
    onClosed: if (!applied) wallpapers.cancel()

    background: Rectangle {
        objectName: sheet.visible ? "geo_open_popup" : ""
        radius: 24
        color: theme.surface
        border.width: theme.comfort ? 2 : 1
        border.color: theme.borderColor
    }

    FileDialog {
        id: picker
        title: "Choisir une image"
        nameFilters: ["Images (*.jpg *.jpeg *.png *.webp *.JPG *.JPEG *.PNG *.WEBP)"]
        currentFolder: app.picturesFolderUrl()
        onAccepted: sheet.error = wallpapers.importFile(selectedFile.toString())
    }

    contentItem: Column {
        id: column
        spacing: 14

        Row {
            spacing: 16
            Text {
                text: "Fond d'écran"
                font.pixelSize: theme.fontPanelTitle
                font.weight: Font.DemiBold
                color: theme.textColor
            }
            Text {
                anchors.baseline: parent.children[0].baseline
                text: wallpapers.previewing ? "Aperçu : appliquez pour le garder." : "Cliquez sur une image pour l'essayer."
                font.pixelSize: theme.fontBody
                color: theme.mutedColor
            }
        }

        ListView {
            id: list
            width: sheet.availableWidth
            height: thumbHeight + labelHeight + 12
            orientation: ListView.Horizontal
            spacing: 14
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            keyNavigationEnabled: true
            model: wallpapers
            readonly property int thumbWidth: theme.comfort ? 176 : 160
            readonly property int thumbHeight: Math.round(thumbWidth * 9 / 16)
            readonly property int labelHeight: theme.fontBody + 10

            delegate: T.AbstractButton {
                id: thumb
                required property int index
                required property string wallpaperId
                required property string label
                required property string source
                width: list.thumbWidth
                height: list.height
                focusPolicy: Qt.StrongFocus
                Accessible.name: "Fond " + label
                readonly property bool selected: wallpapers.selectedId === wallpaperId
                onClicked: { list.currentIndex = index; wallpapers.preview(wallpaperId) }
                Keys.onReturnPressed: clicked()

                contentItem: Column {
                    spacing: 6
                    Rectangle {
                        width: thumb.width
                        height: list.thumbHeight
                        radius: 12
                        clip: true
                        color: "#E3ECF3"
                        border.width: thumb.selected ? theme.focusWidth + 1 : 1
                        border.color: thumb.selected ? theme.accent : theme.borderColor
                        Rectangle {
                            // Aperçu du dégradé « Brume »
                            anchors.fill: parent
                            anchors.margins: parent.border.width
                            radius: 10
                            visible: thumb.source === ""
                            gradient: Gradient {
                                GradientStop { position: 0.0; color: "#D5E4F1" }
                                GradientStop { position: 0.55; color: "#F4EFE5" }
                                GradientStop { position: 1.0; color: "#D3E5D8" }
                            }
                        }
                        Image {
                            anchors.fill: parent
                            anchors.margins: parent.border.width
                            source: thumb.source
                            fillMode: Image.PreserveAspectCrop
                            sourceSize.width: list.thumbWidth
                            sourceSize.height: list.thumbHeight
                            asynchronous: true
                        }
                        FocusRing { visible: thumb.visualFocus; baseRadius: 12 }
                    }
                    Text {
                        width: thumb.width
                        horizontalAlignment: Text.AlignHCenter
                        elide: Text.ElideRight
                        text: thumb.label
                        font.pixelSize: theme.fontBody
                        font.weight: thumb.selected ? Font.DemiBold : Font.Normal
                        color: theme.textColor
                    }
                }
            }

            footer: Item {
                width: list.thumbWidth + 14
                height: list.height
                T.AbstractButton {
                    id: importButton
                    x: 14
                    width: list.thumbWidth
                    height: list.thumbHeight
                    focusPolicy: Qt.StrongFocus
                    hoverEnabled: true
                    Accessible.name: "Importer une image"
                    onClicked: picker.open()
                    Keys.onReturnPressed: clicked()
                    background: Rectangle {
                        radius: 12
                        color: importButton.hovered ? "#E4EDF7" : theme.surfaceAlt
                        border.width: 2
                        border.color: "#9DB1C6"
                        FocusRing { visible: importButton.visualFocus; baseRadius: 12 }
                    }
                    contentItem: Text {
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                        wrapMode: Text.WordWrap
                        text: "+\nImporter une image…"
                        font.pixelSize: theme.fontBody
                        font.weight: Font.DemiBold
                        color: theme.accent
                    }
                }
            }
        }

        Text {
            visible: sheet.error !== ""
            width: sheet.availableWidth
            wrapMode: Text.WordWrap
            text: sheet.error
            font.pixelSize: theme.fontBody
            font.weight: Font.DemiBold
            color: theme.danger
            Accessible.role: Accessible.AlertMessage
        }

        Item {
            width: sheet.availableWidth
            height: theme.controlHeight
            Row {
                spacing: 12
                SdButton {
                    text: "Revenir au fond d'origine"
                    onClicked: { sheet.applied = true; wallpapers.reset(); sheet.close() }
                }
                SdButton {
                    visible: wallpapers.selectedIsImported
                    text: "Retirer cette image"
                    kind: "danger"
                    onClicked: wallpapers.removeImported(wallpapers.selectedId)
                }
            }
            Row {
                anchors.right: parent.right
                spacing: 12
                SdButton { text: "Annuler"; onClicked: sheet.close() }
                SdButton {
                    objectName: "geo_wallpaper_apply"
                    kind: "primary"
                    text: "Appliquer"
                    enabled: wallpapers.previewing
                    onClicked: { if (wallpapers.apply()) { sheet.applied = true; sheet.close() } }
                }
            }
        }
    }
}
