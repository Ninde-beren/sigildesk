// Icône par nom : celle de l'utilisateur si elle existe, sinon celle livrée.
// Sans support SVG, une pastille avec l'initiale prend le relais.
import QtQuick

Item {
    id: icon
    property string name
    property int size: 60

    width: size
    height: size

    Image {
        id: image
        anchors.fill: parent
        source: icons.url(icon.name)
        sourceSize.width: icon.size
        sourceSize.height: icon.size
        smooth: true
        visible: status === Image.Ready
    }

    Rectangle {
        anchors.fill: parent
        visible: image.status !== Image.Ready
        radius: icon.size * 0.28
        color: "#7F93AA"
        Text {
            anchors.centerIn: parent
            text: icon.name.replace("fav-", "").replace("dock-", "").charAt(0).toUpperCase()
            color: "#FFFFFF"
            font.pixelSize: icon.size * 0.45
            font.weight: Font.Bold
        }
    }
}
