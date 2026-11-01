// Salutation et heure, au centre.
import QtQuick

Column {
    id: greeting
    property bool compact: false
    property color ink
    property string userName: ""
    property date now: new Date()

    readonly property int clockSize: compact ? theme.fontClock - 12 : theme.fontClock
    width: Math.max(hello.implicitWidth, clock.implicitWidth)
    height: hello.height + clock.height

    Timer {
        running: true
        repeat: true
        interval: 1000
        onTriggered: {
            greeting.now = new Date()
            interval = (60 - greeting.now.getSeconds()) * 1000 + 50
        }
    }

    Text {
        id: hello
        objectName: "geo_hello"
        anchors.horizontalCenter: parent.horizontalCenter
        height: Math.round(theme.fontTitle * 1.25)
        verticalAlignment: Text.AlignVCenter
        readonly property int hour: greeting.now.getHours()
        text: (hour >= 5 && hour < 18 ? "Bonjour" : "Bonsoir") + (greeting.userName ? " " + greeting.userName : "")
        font.pixelSize: theme.fontTitle
        font.weight: Font.Medium
        color: greeting.ink
    }

    Text {
        id: clock
        objectName: "geo_clock"
        anchors.horizontalCenter: parent.horizontalCenter
        height: Math.round(greeting.clockSize * 1.1)
        verticalAlignment: Text.AlignVCenter
        text: greeting.now.toLocaleTimeString(Qt.locale("fr_FR"), "HH:mm")
        font.pixelSize: greeting.clockSize
        font.weight: Font.Light
        color: greeting.ink
        Accessible.name: "Il est " + text
    }
}
