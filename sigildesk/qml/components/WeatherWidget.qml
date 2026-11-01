// Météo sous la date, posée sur le fond comme la date elle-même : grande icône,
// température en grand, conditions, puis la ville en surtitre discret (et
// l'heure des données quand elles ne sont plus fraîches). Un clic ouvre
// Paramètres › Météo. Masquée quand la météo est désactivée.
import QtQuick
import QtQuick.Templates as T

T.AbstractButton {
    id: widget
    property color ink
    property color inkMuted
    property int maxWidth: 380
    readonly property string mode: weather.state  // off, no_city, loading, unavailable, ok, stale
    readonly property bool hasData: mode === "ok" || mode === "stale"

    readonly property string headline: hasData ? weather.condition
        : mode === "unavailable" ? "Météo indisponible"
        : mode === "loading" ? "Météo…" : "Météo : choisir une ville"

    visible: weather.weatherEnabled
    implicitWidth: Math.min(content.implicitWidth, maxWidth) + 16
    implicitHeight: content.implicitHeight + 8
    focusPolicy: Qt.StrongFocus
    hoverEnabled: true
    Accessible.name: (hasData ? weather.temperature + ", " : "") + headline
        + (weather.cityName ? ", " + weather.cityName : "") + (mode === "stale" ? ", " + weather.updatedLabel : "")
    Accessible.description: "Ouvre les réglages de la météo"
    Keys.onReturnPressed: clicked()
    Keys.onEnterPressed: clicked()

    background: Rectangle {
        // Aucun fond au repos ; un voile léger seulement au survol.
        radius: 14
        color: widget.hovered ? Qt.rgba(1, 1, 1, 0.18) : "transparent"
        FocusRing { visible: widget.visualFocus; baseRadius: 14 }
    }

    contentItem: Item {
        Row {
            id: content
            x: 8
            y: 4
            spacing: 12

            Icon {
                anchors.verticalCenter: parent.verticalCenter
                name: widget.hasData ? weather.iconName
                    : widget.mode === "unavailable" ? "meteo-indisponible" : "meteo-eclaircies"
                size: theme.comfort ? 54 : 48
                opacity: widget.hasData || widget.mode === "unavailable" ? 1 : 0.6
            }
            Column {
                anchors.verticalCenter: parent.verticalCenter
                width: Math.min(implicitWidth, widget.maxWidth - (theme.comfort ? 66 : 60))

                Row {
                    spacing: 10
                    Text {
                        visible: widget.hasData
                        anchors.baseline: condition.baseline
                        text: weather.temperature
                        font.pixelSize: theme.fontTitle + 6
                        font.weight: Font.DemiBold
                        color: widget.ink
                    }
                    Text {
                        id: condition
                        objectName: "geo_weather_condition"
                        height: Math.round((theme.fontTitle + 6) * 1.2)
                        verticalAlignment: Text.AlignBottom
                        bottomPadding: 3
                        text: widget.headline
                        font.pixelSize: theme.fontBody + 1
                        font.weight: Font.Medium
                        color: widget.ink
                    }
                }
                Text {
                    objectName: "geo_weather_detail"
                    visible: weather.cityName !== ""
                    width: Math.min(implicitWidth, widget.maxWidth - (theme.comfort ? 66 : 60))
                    text: weather.cityName
                    elide: Text.ElideRight
                    font.pixelSize: theme.fontSmall
                    font.weight: Font.DemiBold
                    font.capitalization: Font.AllUppercase
                    font.letterSpacing: 1
                    color: widget.inkMuted
                }
                Text {
                    // Hors connexion : l'heure des données, sur sa propre ligne.
                    objectName: "geo_weather_updated"
                    visible: widget.mode === "stale"
                    text: visible ? weather.updatedLabel : ""
                    font.pixelSize: theme.fontSmall
                    color: widget.inkMuted
                }
            }
        }
    }
}
