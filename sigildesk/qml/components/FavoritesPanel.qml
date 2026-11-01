// « Mes favoris » : jusqu'à 12 liens. Un clic ouvre le site ; « Modifier la
// liste » permet de renommer, réordonner ou retirer. Panneau séparé de l'accueil.
import QtQuick
import QtQuick.Templates as T

PanelFrame {
    id: panel
    title: "Mes favoris"
    preferredWidth: 880
    preferredHeight: 600
    property bool editing: false
    signal editRequested(int row)
    signal removeRequested(int row)

    onClosed: editing = false
    onOpened: Qt.callLater(function() { if (favorites.count > 0 && !panel.editing) grid.itemAt(0).forceActiveFocus() })

    headerExtra: [
        Text {
            anchors.verticalCenter: parent.verticalCenter
            text: favorites.count + " / " + favorites.maximum
            font.pixelSize: theme.fontBody
            color: theme.mutedColor
        },
        SdButton {
            objectName: "geo_fav_add"
            kind: "primary"
            text: "Ajouter"
            enabled: favorites.canAdd
            onClicked: panel.editRequested(-1)
        },
        SdButton {
            visible: favorites.count > 0
            text: panel.editing ? "Terminer" : "Modifier la liste"
            onClicked: panel.editing = !panel.editing
        }
    ]

    Text {
        anchors.centerIn: parent
        width: Math.min(parent.width, 520)
        visible: favorites.count === 0
        horizontalAlignment: Text.AlignHCenter
        wrapMode: Text.WordWrap
        text: "Aucun favori pour l'instant.\nCliquez sur « Ajouter » pour garder un site sous la main."
        font.pixelSize: theme.fontBody + 1
        color: theme.mutedColor
    }

    // Consultation : grille de cartes, un clic ouvre le site.
    Flickable {
        id: cards
        anchors.fill: parent
        anchors.rightMargin: 14
        visible: !panel.editing && favorites.count > 0
        clip: true
        contentHeight: gridLayout.height
        boundsBehavior: Flickable.StopAtBounds

        Grid {
            id: gridLayout
            width: parent.width
            columns: Math.max(2, Math.floor((width + 16) / 250))
            spacing: 16

            Repeater {
                id: grid
                model: favorites
                delegate: T.AbstractButton {
                    id: card
                    required property int index
                    required property string name
                    required property string iconName
                    required property string host
                    width: (gridLayout.width - (gridLayout.columns - 1) * gridLayout.spacing) / gridLayout.columns
                    height: theme.comfort ? 104 : 92
                    focusPolicy: Qt.StrongFocus
                    hoverEnabled: true
                    Accessible.name: name + ", " + host
                    onClicked: { if (app.openFavorite(index) === "ok") panel.close() }
                    Keys.onReturnPressed: clicked()
                    Keys.onEnterPressed: clicked()

                    background: Rectangle {
                        radius: 18
                        color: card.down ? theme.pressed : card.hovered ? "#E9EFF6" : theme.surfaceAlt
                        border.width: theme.comfort ? 2 : 1
                        border.color: theme.borderColor
                        FocusRing { visible: card.visualFocus; baseRadius: 18 }
                    }
                    contentItem: Row {
                        spacing: 14
                        leftPadding: 14
                        Icon {
                            anchors.verticalCenter: parent.verticalCenter
                            name: card.iconName
                            size: theme.comfort ? 52 : 46
                        }
                        Column {
                            anchors.verticalCenter: parent.verticalCenter
                            width: card.width - (theme.comfort ? 52 : 46) - 44
                            spacing: 2
                            Text {
                                width: parent.width
                                text: card.name
                                elide: Text.ElideRight
                                font.pixelSize: theme.fontBody
                                font.weight: Font.DemiBold
                                color: theme.textColor
                            }
                            Text {
                                width: parent.width
                                text: card.host
                                elide: Text.ElideMiddle
                                font.pixelSize: theme.fontSmall
                                color: theme.mutedColor
                            }
                        }
                    }
                }
            }
        }
    }

    // Modification : une ligne par favori, boutons écrits en toutes lettres.
    ListView {
        id: list
        anchors.fill: parent
        anchors.rightMargin: 14
        visible: panel.editing
        clip: true
        spacing: 8
        boundsBehavior: Flickable.StopAtBounds
        model: favorites
        delegate: Rectangle {
            id: line
            required property int index
            required property string name
            required property string iconName
            required property string host
            width: list.width
            height: theme.controlHeight + 16
            radius: 14
            color: theme.surfaceAlt

            Icon {
                id: lineIcon
                anchors.left: parent.left
                anchors.leftMargin: 12
                anchors.verticalCenter: parent.verticalCenter
                name: line.iconName
                size: theme.controlHeight - 8
            }
            Column {
                anchors.left: lineIcon.right
                anchors.leftMargin: 12
                anchors.right: actions.left
                anchors.rightMargin: 12
                anchors.verticalCenter: parent.verticalCenter
                Text {
                    width: parent.width
                    text: line.name
                    elide: Text.ElideRight
                    font.pixelSize: theme.fontBody
                    font.weight: Font.DemiBold
                    color: theme.textColor
                }
                Text {
                    width: parent.width
                    text: line.host
                    elide: Text.ElideMiddle
                    font.pixelSize: theme.fontSmall
                    color: theme.mutedColor
                }
            }
            Row {
                id: actions
                anchors.right: parent.right
                anchors.rightMargin: 8
                anchors.verticalCenter: parent.verticalCenter
                spacing: 6
                SdButton { text: "Monter"; enabled: line.index > 0; onClicked: favorites.move(line.index, -1) }
                SdButton { text: "Descendre"; enabled: line.index < favorites.count - 1; onClicked: favorites.move(line.index, 1) }
                SdButton { text: "Modifier"; onClicked: panel.editRequested(line.index) }
                SdButton { text: "Retirer"; kind: "danger"; onClicked: panel.removeRequested(line.index) }
            }
        }
    }
    ScrollHint { flick: cards }
    ScrollHint { flick: list }
}
