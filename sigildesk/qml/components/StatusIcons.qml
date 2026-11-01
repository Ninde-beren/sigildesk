// Pastille d'état : Wi-Fi (force du signal), Bluetooth, batterie et charge.
import QtQuick

Rectangle {
    id: pill
    property bool onDark: false
    readonly property int iconSize: theme.comfort ? 26 : 22
    readonly property bool lowBattery: systemStatus.batteryPercent >= 0 && systemStatus.batteryPercent <= 15 && !systemStatus.charging

    implicitWidth: row.implicitWidth + 28
    radius: height / 2
    color: Qt.rgba(1, 1, 1, onDark || theme.comfort ? 0.92 : 0.74)
    border.width: theme.comfort ? 2 : 1
    border.color: theme.borderColor
    Accessible.role: Accessible.StaticText
    Accessible.name: [systemStatus.networkLabel, systemStatus.bluetoothLabel, systemStatus.batteryLabel]
        .filter(function(part) { return part !== "" }).join(", ")

    Row {
        id: row
        anchors.centerIn: parent
        spacing: 14

        Icon {
            objectName: "geo_status_network"
            anchors.verticalCenter: parent.verticalCenter
            name: systemStatus.networkIcon
            size: pill.iconSize
        }
        Icon {
            visible: systemStatus.bluetooth !== "absent"
            anchors.verticalCenter: parent.verticalCenter
            name: systemStatus.bluetoothIcon
            size: pill.iconSize
        }
        Row {
            visible: systemStatus.batteryPercent >= 0
            anchors.verticalCenter: parent.verticalCenter
            spacing: 7
            BatteryIcon {
                anchors.verticalCenter: parent.verticalCenter
                level: systemStatus.batteryPercent
                charging: systemStatus.charging
            }
            Text {
                anchors.verticalCenter: parent.verticalCenter
                text: systemStatus.batteryPercent + " %"
                font.pixelSize: theme.fontBody
                font.weight: Font.DemiBold
                color: pill.lowBattery ? theme.danger : theme.textColor
            }
        }
    }
}
