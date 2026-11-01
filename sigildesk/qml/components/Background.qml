// Fond de SigilDesk : image recadrée au centre, sans étirement, sur un dégradé
// « Brume » qui sert aussi de repli. Deux voiles légers gardent lisibles les
// textes posés directement sur l'image, même très contrastée.
import QtQuick

Item {
    id: bg
    property string source
    property bool dark: false
    property bool strongVeil: false
    readonly property bool ready: source === "" || image.status === Image.Ready || image.status === Image.Error

    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#D5E4F1" }
            GradientStop { position: 0.55; color: "#F4EFE5" }
            GradientStop { position: 1.0; color: "#D3E5D8" }
        }
    }

    Image {
        id: image
        anchors.fill: parent
        source: bg.source
        fillMode: Image.PreserveAspectCrop
        horizontalAlignment: Image.AlignHCenter
        verticalAlignment: Image.AlignVCenter
        asynchronous: true
        cache: false
        smooth: true
        // Décodé à la taille de l'écran : pas de pleine résolution en mémoire.
        sourceSize.width: bg.width > 0 ? Math.ceil(bg.width) : 0
        sourceSize.height: bg.height > 0 ? Math.ceil(bg.height) : 0
        visible: status === Image.Ready
    }

    readonly property real veil: strongVeil ? 0.62 : 0.48
    readonly property color veilColor: dark ? Qt.rgba(0.04, 0.07, 0.11, veil) : Qt.rgba(1, 1, 1, veil)
    readonly property color clearColor: dark ? Qt.rgba(0.04, 0.07, 0.11, 0) : Qt.rgba(1, 1, 1, 0)

    Rectangle {
        anchors { left: parent.left; right: parent.right; top: parent.top }
        height: Math.min(parent.height * 0.40, 300)
        gradient: Gradient {
            GradientStop { position: 0.0; color: bg.veilColor }
            GradientStop { position: 1.0; color: bg.clearColor }
        }
    }

    Rectangle {
        anchors { left: parent.left; right: parent.right; bottom: parent.bottom }
        height: Math.min(parent.height * 0.22, 160)
        gradient: Gradient {
            GradientStop { position: 0.0; color: bg.clearColor }
            GradientStop { position: 1.0; color: bg.veilColor }
        }
    }
}
