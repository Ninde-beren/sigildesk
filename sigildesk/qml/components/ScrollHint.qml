// Barre discrète qui signale qu'un panneau défile (molette ou pavé tactile).
// Se place à côté de la Flickable, dans le même parent.
import QtQuick

Rectangle {
    property Flickable flick

    visible: flick !== null && flick.visible && flick.contentHeight > flick.height + 1
    width: 6
    radius: 3
    color: theme.mutedColor
    opacity: 0.55
    x: flick ? flick.x + flick.width + 8 : 0
    y: flick ? flick.y + flick.visibleArea.yPosition * flick.height : 0
    height: flick ? Math.max(28, flick.visibleArea.heightRatio * flick.height) : 0
}
