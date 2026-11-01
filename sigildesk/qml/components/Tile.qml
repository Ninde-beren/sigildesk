// Une tuile de l'accueil : icône 60–64 px et libellé, sur une carte claire.
import QtQuick
import QtQuick.Templates as T

T.AbstractButton {
    id: tile
    required property string tileId
    required property string label
    required property string iconName
    required property string hint
    required property bool needsSetup
    // Tuile de favori (troisième rangée) : ouvre ce favori au lieu d'une tuile fixe.
    property int favoriteIndex: -1
    // Les flèches sont confiées à la grille (aucune référence retour vers elle :
    // Qt 6.10 refuse la dépendance circulaire Tile ↔ TileGrid).
    signal navigate(int key)

    objectName: "geo_tile_" + tileId
    implicitWidth: theme.tileWidth
    implicitHeight: theme.tileHeight
    focusPolicy: Qt.StrongFocus
    hoverEnabled: true
    text: label
    Accessible.name: label
    Accessible.description: needsSetup ? "À régler dans Paramètres" : hint

    onClicked: favoriteIndex >= 0 ? app.openFavorite(favoriteIndex) : app.openTile(tileId)
    Keys.onReturnPressed: clicked()
    Keys.onEnterPressed: clicked()
    Keys.onLeftPressed: navigate(Qt.Key_Left)
    Keys.onRightPressed: navigate(Qt.Key_Right)
    Keys.onUpPressed: navigate(Qt.Key_Up)
    Keys.onDownPressed: navigate(Qt.Key_Down)

    background: Item {
        // Ombre simulée par un rectangle décalé : aucun effet graphique coûteux.
        Rectangle {
            anchors.fill: parent
            anchors.topMargin: 4
            anchors.bottomMargin: -4
            radius: theme.radius
            color: "#14263A"
            opacity: tile.down ? 0.06 : 0.12
        }
        Rectangle {
            id: card
            anchors.fill: parent
            radius: theme.radius
            color: tile.down ? theme.pressed : Qt.rgba(1, 1, 1, tile.hovered ? 1.0 : (wallpapers.tone === "dark" ? 0.96 : theme.cardOpacity))
            border.width: theme.comfort ? 2 : 1
            border.color: tile.hovered ? "#2763C966" : theme.borderColor
            FocusRing { visible: tile.visualFocus; baseRadius: theme.radius }
        }
    }

    // Sans nom affiché (Paramètres › Affichage), l'icône occupe toute la tuile.
    readonly property bool showLabel: app.showLabels

    contentItem: Item {
        Column {
            anchors.centerIn: parent
            spacing: 8

            Icon {
                objectName: "geo_tile_icon_" + tile.tileId
                anchors.horizontalCenter: parent.horizontalCenter
                name: tile.iconName
                size: tile.showLabel ? theme.iconSize : Math.min(tile.width, tile.height) - 16
            }
            Text {
                visible: tile.showLabel
                objectName: "geo_tile_label_" + tile.tileId
                anchors.horizontalCenter: parent.horizontalCenter
                width: tile.width - 12
                horizontalAlignment: Text.AlignHCenter
                text: tile.label
                elide: Text.ElideRight
                font.pixelSize: theme.fontLabel
                font.weight: Font.DemiBold
                color: theme.textColor
            }
        }
    }

    Rectangle {
        // Pastille « À régler » (messagerie pas encore choisie).
        visible: tile.needsSetup
        anchors.top: parent.top
        anchors.right: parent.right
        anchors.topMargin: -12
        anchors.rightMargin: -14
        height: badge.implicitHeight + 6
        width: badge.implicitWidth + 14
        radius: height / 2
        color: "#F2A93B"
        border.color: "#FFFFFF"
        border.width: 2
        Text {
            id: badge
            anchors.centerIn: parent
            text: "À régler"
            font.pixelSize: theme.fontSmall - 2
            font.weight: Font.DemiBold
            color: "#2A1A00"
        }
    }
}
