// Batterie dessinée en QML : le remplissage suit le niveau, un éclair signale la charge.
import QtQuick

Item {
    id: battery
    property int level: 0
    property bool charging: false

    implicitWidth: theme.comfort ? 32 : 28
    implicitHeight: theme.comfort ? 16 : 14

    Rectangle {
        id: body
        width: parent.width - 3
        height: parent.height
        radius: 3
        color: "transparent"
        border.width: 2
        border.color: theme.textColor

        Rectangle {
            x: 3
            y: 3
            height: parent.height - 6
            width: Math.max(2, (parent.width - 6) * Math.max(0, Math.min(100, battery.level)) / 100)
            radius: 1
            color: battery.level <= 15 && !battery.charging ? theme.danger
                 : battery.level <= 30 ? "#D9932B" : "#3E9B5F"
        }
    }
    Rectangle {
        x: body.width
        anchors.verticalCenter: parent.verticalCenter
        width: 3
        height: parent.height * 0.45
        radius: 1
        color: theme.textColor
    }
    Icon {
        visible: battery.charging
        anchors.centerIn: body
        name: "statut-charge"
        size: battery.height + 6
    }
}
