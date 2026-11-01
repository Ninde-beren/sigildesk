// Grille de l'accueil : en haut les services web, puis l'ordinateur, et, si la
// place le permet, les quatre premiers favoris (dans l'ordre choisi dans
// « Mes favoris »). Flèches du clavier pour se déplacer, Entrée ou Espace pour ouvrir.
import QtQuick

Column {
    id: grid
    property bool onDark: false
    property color ink
    readonly property int columns: 4
    property bool showFavorites: false
    readonly property int rows: showFavorites && favorites.top.length > 0 ? 3 : 2
    property var tileItems: []

    spacing: 0
    width: columns * theme.tileWidth + (columns - 1) * theme.tileGap

    function register(index, item) { tileItems[index] = item }

    function focusFirst() {
        if (tileItems[0])
            tileItems[0].forceActiveFocus()
    }

    function moveFocus(index, key) {
        let row = Math.floor(index / columns)
        let col = index % columns
        if (key === Qt.Key_Left) col = Math.max(0, col - 1)
        else if (key === Qt.Key_Right) col = Math.min(columns - 1, col + 1)
        else if (key === Qt.Key_Up) row = Math.max(0, row - 1)
        else if (key === Qt.Key_Down) row = Math.min(rows - 1, row + 1)
        // Rangée de favoris incomplète : on va sur la dernière tuile présente.
        while (col > 0 && !(tileItems[row * columns + col] && tileItems[row * columns + col].visible))
            col -= 1
        const target = tileItems[row * columns + col]
        if (target && target.visible)
            target.forceActiveFocus(Qt.TabFocusReason)
    }

    Row {
        spacing: theme.tileGap
        Repeater {
            model: webTiles
            delegate: Tile {
                id: webTile
                required property int index
                onNavigate: function(key) { grid.moveFocus(index, key) }
                Component.onCompleted: grid.register(index, webTile)
            }
        }
    }
    Item { width: 1; height: theme.tileGap }
    Row {
        spacing: theme.tileGap
        Repeater {
            model: localTiles
            delegate: Tile {
                id: localTile
                required property int index
                onNavigate: function(key) { grid.moveFocus(grid.columns + index, key) }
                Component.onCompleted: grid.register(grid.columns + index, localTile)
            }
        }
    }
    Item { width: 1; height: theme.tileGap; visible: grid.rows === 3 }
    Row {
        objectName: "geo_fav_row"
        visible: grid.rows === 3
        spacing: theme.tileGap
        Repeater {
            model: favorites.top
            delegate: Tile {
                id: favoriteTile
                required property var modelData
                objectName: "geo_fav_" + modelData.index
                tileId: "favori-" + modelData.index
                label: modelData.name
                iconName: modelData.iconName
                hint: "Ouvrir " + modelData.host
                needsSetup: false
                favoriteIndex: modelData.index
                onNavigate: function(key) { grid.moveFocus(2 * grid.columns + modelData.index, key) }
                Component.onCompleted: grid.register(2 * grid.columns + modelData.index, favoriteTile)
            }
        }
    }
}
