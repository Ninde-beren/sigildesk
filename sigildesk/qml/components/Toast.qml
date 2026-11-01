// Message bref au-dessus du dock (« Ouverture d'Internet… »), masqué après 5 s.
import QtQuick

Rectangle {
    id: toast
    visible: false
    width: Math.min(label.implicitWidth + 48, (parent ? parent.width : 800) - 64)
    height: label.height + 22
    radius: Math.min(height / 2, 24)
    color: "#EE1D2935"
    Accessible.role: Accessible.AlertMessage
    Accessible.name: label.text

    function show(message) {
        label.text = message
        visible = true
        hideTimer.restart()
    }

    Text {
        id: label
        anchors.centerIn: parent
        width: toast.width - 48
        horizontalAlignment: Text.AlignHCenter
        wrapMode: Text.WordWrap
        font.pixelSize: theme.fontBody
        color: "#FFFFFF"
    }

    Timer {
        id: hideTimer
        interval: 5000
        onTriggered: toast.visible = false
    }
}
