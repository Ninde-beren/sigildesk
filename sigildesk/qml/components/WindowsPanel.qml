// Toutes les fenêtres ouvertes, quand le dock n'a pas la place de toutes les montrer.
import QtQuick
import QtQuick.Templates as T

PanelFrame {
    id: panel
    title: "Fenêtres ouvertes"
    preferredWidth: 620
    preferredHeight: 480

    Flickable {
        id: scroller
        anchors.fill: parent
        anchors.rightMargin: 14
        clip: true
        contentHeight: list.height
        boundsBehavior: Flickable.StopAtBounds

        Column {
            id: list
            width: parent.width
            spacing: 8
            Repeater {
                model: openWindows
                delegate: T.AbstractButton {
                    id: item
                    required property string windowId
                    required property string label
                    required property string windowIcon
                    required property string title
                    width: list.width
                    height: theme.controlHeight + 16
                    focusPolicy: Qt.StrongFocus
                    hoverEnabled: true
                    Accessible.name: "Revenir à " + label
                    onClicked: { panel.close(); openWindows.activate(windowId) }
                    Keys.onReturnPressed: clicked()
                    background: Rectangle {
                        radius: 14
                        color: item.down ? theme.pressed : item.hovered ? "#E9EFF6" : theme.surfaceAlt
                        FocusRing { visible: item.visualFocus; baseRadius: 14 }
                    }
                    contentItem: Row {
                        spacing: 14
                        leftPadding: 12
                        Icon {
                            anchors.verticalCenter: parent.verticalCenter
                            name: item.windowIcon
                            size: theme.controlHeight - 6
                        }
                        Column {
                            anchors.verticalCenter: parent.verticalCenter
                            width: item.width - theme.controlHeight - 40
                            Text {
                                width: parent.width
                                text: item.label
                                elide: Text.ElideRight
                                font.pixelSize: theme.fontBody
                                font.weight: Font.DemiBold
                                color: theme.textColor
                            }
                            Text {
                                width: parent.width
                                text: item.title
                                elide: Text.ElideRight
                                font.pixelSize: theme.fontSmall
                                color: theme.mutedColor
                            }
                        }
                    }
                }
            }
        }
    }
    ScrollHint { flick: scroller }
}
