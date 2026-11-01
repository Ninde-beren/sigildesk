// Paramètres : affichage (mode confort, fond, prénom), messagerie, dossiers des
// tuiles locales, météo, applications, maintenance, à propos. Chaque réglage
// s'applique et s'enregistre aussitôt. Les sections se désignent par leur nom
// (`openSectionNamed`), jamais par un numéro.
import QtQuick
import QtQuick.Dialogs
import QtQuick.Templates as T

PanelFrame {
    id: panel
    title: "Paramètres"
    preferredWidth: 960
    preferredHeight: 640
    property int section: 0
    property var tools: []
    property var associations: []
    property var decoding: ({})  // rapport du décodage vidéo matériel (status, label, hint)
    property bool checking: false
    signal wallpaperRequested()
    signal minimizeRequested()
    signal quitRequested()

    readonly property var sections: ["Affichage", "Messagerie", "Dossiers", "Météo", "Applications", "Maintenance", "À propos"]
    readonly property var sectionIds: ["affichage", "messagerie", "dossiers", "meteo", "applications", "maintenance", "apropos"]
    readonly property string current: sectionIds[section]

    function openSection(index) {
        section = index
        open()
        Qt.callLater(function() { navRepeater.itemAt(index).forceActiveFocus() })
    }

    function openSectionNamed(name) {
        openSection(Math.max(0, sectionIds.indexOf(name)))
    }

    Connections {
        target: app
        function onDiagnosticsReady(toolList, associationList, decodingReport) {
            panel.tools = toolList
            panel.associations = associationList
            panel.decoding = decodingReport
            panel.checking = false
        }
    }

    // --- Navigation à gauche ------------------------------------------------
    Column {
        id: nav
        width: theme.comfort ? 230 : 200
        spacing: 6
        Repeater {
            id: navRepeater
            model: panel.sections
            delegate: T.AbstractButton {
                id: navButton
                required property int index
                required property string modelData
                width: nav.width
                height: theme.controlHeight
                focusPolicy: Qt.StrongFocus
                hoverEnabled: true
                Accessible.name: modelData
                onClicked: panel.section = index
                Keys.onReturnPressed: clicked()
                Keys.onDownPressed: navRepeater.itemAt(Math.min(index + 1, panel.sections.length - 1)).forceActiveFocus(Qt.TabFocusReason)
                Keys.onUpPressed: navRepeater.itemAt(Math.max(index - 1, 0)).forceActiveFocus(Qt.TabFocusReason)
                background: Rectangle {
                    radius: 12
                    color: panel.section === navButton.index ? "#DCE7F7" : navButton.hovered ? theme.surfaceAlt : "transparent"
                    FocusRing { visible: navButton.visualFocus; baseRadius: 12 }
                }
                contentItem: Text {
                    leftPadding: 14
                    verticalAlignment: Text.AlignVCenter
                    text: navButton.modelData
                    font.pixelSize: theme.fontBody
                    font.weight: panel.section === navButton.index ? Font.DemiBold : Font.Normal
                    color: theme.textColor
                }
            }
        }
    }

    Rectangle {
        id: separator
        anchors.left: nav.right
        anchors.leftMargin: 20
        height: parent.height
        width: 1
        color: theme.borderColor
    }

    // --- Contenu -------------------------------------------------------------
    Flickable {
        id: page
        anchors { left: separator.right; leftMargin: 24; right: parent.right; rightMargin: 14; top: parent.top; bottom: parent.bottom }
        clip: true
        contentHeight: pages.height
        boundsBehavior: Flickable.StopAtBounds

        Item {
            id: pages
            width: page.width
            height: [affichage, messagerie, dossiers, meteo, applications, maintenance, apropos][panel.section].height

            // Affichage -------------------------------------------------------
            Column {
                id: affichage
                width: parent.width
                spacing: 20
                visible: panel.current === "affichage"

                SettingCard {
                    title: "Mode confort"
                    description: "Textes plus grands, contrastes et boutons renforcés."
                    SdSwitch {
                        objectName: "geo_comfort_switch"
                        checked: theme.comfort
                        Accessible.name: "Mode confort"
                        onToggled: {
                            const error = app.setComfort(checked)
                            if (error !== "") checked = theme.comfort
                        }
                    }
                }

                SettingCard {
                    title: "Noms sous les icônes"
                    description: "Sans les noms, les icônes de l'accueil sont plus grandes."
                    SdSwitch {
                        objectName: "geo_labels_switch"
                        checked: app.showLabels
                        Accessible.name: "Noms sous les icônes"
                        onToggled: {
                            const error = app.setShowLabels(checked)
                            if (error !== "") checked = app.showLabels
                        }
                    }
                }

                SettingCard {
                    title: "Fond d'écran"
                    description: "Une image livrée ou l'une de vos photos."
                    Row {
                        spacing: 16
                        Rectangle {
                            width: 128
                            height: 72
                            radius: 10
                            clip: true
                            color: "#E6EDF3"
                            Image {
                                anchors.fill: parent
                                source: wallpapers.source
                                fillMode: Image.PreserveAspectCrop
                                sourceSize.width: 128
                                sourceSize.height: 72
                                asynchronous: true
                            }
                        }
                        SdButton {
                            anchors.verticalCenter: parent.verticalCenter
                            text: "Changer le fond d'écran"
                            onClicked: panel.wallpaperRequested()
                        }
                    }
                }

                SettingCard {
                    title: "Prénom affiché"
                    description: "Pour la salutation de l'accueil (facultatif)."
                    Row {
                        spacing: 12
                        SdTextField {
                            id: nameField
                            width: 280
                            text: app.userName
                            placeholderText: "Prénom"
                            maximumLength: 30
                            onAccepted: nameSave.clicked()
                        }
                        SdButton {
                            id: nameSave
                            text: "Enregistrer"
                            onClicked: nameStatus.text = app.setUserName(nameField.text) || "Enregistré."
                        }
                        Text {
                            id: nameStatus
                            anchors.verticalCenter: parent.verticalCenter
                            font.pixelSize: theme.fontBody
                            color: theme.mutedColor
                        }
                    }
                }
            }

            // Messagerie -------------------------------------------------------
            Column {
                id: messagerie
                width: parent.width
                spacing: 6
                visible: panel.current === "messagerie"
                property string choice: app.mailProvider

                Text {
                    width: parent.width
                    wrapMode: Text.WordWrap
                    text: "Choisissez le site de votre messagerie. Le bouton Mails de l'accueil l'ouvrira dans le navigateur."
                    font.pixelSize: theme.fontBody
                    color: theme.mutedColor
                    bottomPadding: 8
                }
                Repeater {
                    model: app.mailProviders()
                    delegate: SdRadio {
                        required property var modelData
                        text: modelData.label
                        checked: messagerie.choice === modelData.id
                        onClicked: messagerie.choice = modelData.id
                    }
                }
                SdRadio {
                    text: "Autre adresse"
                    checked: messagerie.choice === "autre"
                    onClicked: messagerie.choice = "autre"
                }
                SdTextField {
                    id: customMail
                    visible: messagerie.choice === "autre"
                    width: Math.min(parent.width, 480)
                    placeholderText: "adresse du site de messagerie"
                    text: app.mailProvider === "autre" ? app.mailUrl : ""
                }
                Row {
                    spacing: 12
                    topPadding: 10
                    SdButton {
                        kind: "primary"
                        text: "Enregistrer"
                        enabled: messagerie.choice !== ""
                        onClicked: mailStatus.text = app.setMail(messagerie.choice, customMail.text) || "Messagerie enregistrée."
                    }
                    Text {
                        id: mailStatus
                        anchors.verticalCenter: parent.verticalCenter
                        width: messagerie.width - 200
                        wrapMode: Text.WordWrap
                        font.pixelSize: theme.fontBody
                        color: theme.mutedColor
                    }
                }
            }

            // Dossiers ---------------------------------------------------------------
            // Le dossier qu'ouvre chaque tuile locale : un dossier habituel (clé XDG)
            // ou un chemin choisi avec le sélecteur ; `app.folderSettings` donne tout.
            Column {
                id: dossiers
                width: parent.width
                spacing: 20
                visible: panel.current === "dossiers"
                property string statusTile: ""
                property string status: ""

                Text {
                    width: parent.width
                    wrapMode: Text.WordWrap
                    text: "Le dossier qu'ouvre chaque tuile du bas de l'accueil : un dossier de l'ordinateur, "
                        + "une clé USB ou un disque externe. S'il est débranché, le dossier personnel s'ouvre à sa place."
                    font.pixelSize: theme.fontBody
                    color: theme.mutedColor
                }

                FolderDialog {
                    id: folderPicker
                    property string tileId: ""
                    onAccepted: {
                        dossiers.statusTile = tileId
                        dossiers.status = app.setFolderFromUrl(tileId, selectedFolder.toString()) || "Dossier enregistré."
                    }
                }

                Repeater {
                    model: app.folderSettings
                    delegate: SettingCard {
                        required property var modelData
                        title: modelData.label
                        description: modelData.found ? "Dossier actuel :"
                                                     : "Dossier introuvable (le dossier personnel s'ouvre à sa place) :"
                        Column {
                            width: parent.width
                            spacing: 10
                            Text {
                                width: parent.width
                                wrapMode: Text.WrapAnywhere
                                text: modelData.custom ? modelData.setting : modelData.path
                                font.pixelSize: theme.fontBody
                                font.weight: Font.DemiBold
                                color: modelData.found ? theme.textColor : theme.danger
                            }
                            Row {
                                spacing: 12
                                SdButton {
                                    text: "Choisir un dossier…"
                                    Accessible.description: "Choisir le dossier qu'ouvre la tuile " + modelData.label
                                    onClicked: {
                                        folderPicker.tileId = modelData.id
                                        folderPicker.title = "Dossier pour « " + modelData.label + " »"
                                        folderPicker.currentFolder = app.folderUrl(modelData.id)
                                        folderPicker.open()
                                    }
                                }
                                SdButton {
                                    visible: modelData.custom
                                    text: "Revenir à « " + modelData.defaultLabel + " »"
                                    onClicked: {
                                        dossiers.statusTile = modelData.id
                                        dossiers.status = app.resetFolder(modelData.id) || "Dossier habituel rétabli."
                                    }
                                }
                                Text {
                                    anchors.verticalCenter: parent.verticalCenter
                                    visible: dossiers.statusTile === modelData.id && dossiers.status !== ""
                                    text: dossiers.status
                                    font.pixelSize: theme.fontBody
                                    color: theme.mutedColor
                                }
                            }
                        }
                    }
                }
            }

            // Météo ------------------------------------------------------------------
            Column {
                id: meteo
                width: parent.width
                spacing: 20
                visible: panel.current === "meteo"

                SettingCard {
                    title: "Afficher la météo"
                    description: "Sous la date, en haut de l'accueil : température, temps qu'il fait et ville."
                    SdSwitch {
                        objectName: "geo_weather_switch"
                        checked: weather.weatherEnabled
                        Accessible.name: "Afficher la météo"
                        onToggled: {
                            const error = weather.setEnabled(checked)
                            if (error !== "") checked = weather.weatherEnabled
                        }
                    }
                }

                SettingCard {
                    title: "Ville"
                    description: weather.cityLabel !== "" ? "Ville actuelle : " + weather.cityLabel + "."
                                                          : "Aucune ville choisie. Tapez son nom puis choisissez-la dans la liste."
                    Column {
                        width: parent.width
                        spacing: 8
                        Row {
                            spacing: 12
                            SdTextField {
                                id: cityField
                                width: Math.min(340, meteo.width - 220)
                                placeholderText: "Nom de la ville, par exemple Tours"
                                maximumLength: 80
                                onAccepted: weather.search(text)
                            }
                            SdButton {
                                text: "Rechercher"
                                enabled: !weather.searching
                                onClicked: weather.search(cityField.text)
                            }
                        }
                        Text {
                            visible: weather.searchMessage !== ""
                            width: parent.width
                            wrapMode: Text.WordWrap
                            text: weather.searchMessage
                            font.pixelSize: theme.fontBody
                            color: theme.mutedColor
                            Accessible.role: Accessible.AlertMessage
                        }
                        Repeater {
                            model: weather.searchResults
                            delegate: SdRadio {
                                required property var modelData
                                width: parent ? parent.width : 400
                                text: modelData.label
                                checked: false
                                onClicked: weather.chooseCity(modelData.index)
                            }
                        }
                    }
                }

                Text {
                    width: parent.width
                    wrapMode: Text.WordWrap
                    text: weather.attribution + ". Mise à jour toutes les heures. "
                        + "La recherche envoie le nom tapé à Open-Meteo, la météo les coordonnées de la ville choisie ; "
                        + "aucune géolocalisation."
                    font.pixelSize: theme.fontSmall
                    color: theme.mutedColor
                }
            }

            // Applications -------------------------------------------------------
            Column {
                id: applications
                width: parent.width
                spacing: 6
                visible: panel.current === "applications"

                Text {
                    text: "Navigateur utilisé"
                    font.pixelSize: theme.fontBody
                    font.weight: Font.DemiBold
                    color: theme.textColor
                }
                Repeater {
                    model: app.browserChoices()
                    delegate: SdRadio {
                        required property var modelData
                        text: modelData.label
                        checked: app.browser === modelData.id
                        onClicked: app.setBrowser(modelData.id)
                    }
                }
                Item { width: 1; height: 12 }
                Row {
                    spacing: 12
                    SdButton {
                        text: panel.checking ? "Vérification…" : "Vérifier les applications"
                        enabled: !panel.checking
                        onClicked: { panel.checking = true; app.runDiagnostics() }
                    }
                }
                Repeater {
                    model: panel.tools
                    delegate: Text {
                        required property var modelData
                        width: applications.width
                        elide: Text.ElideRight
                        text: (modelData.path ? "✓  " : "–  ") + modelData.label + (modelData.path ? "" : " : absent")
                        font.pixelSize: theme.fontBody
                        color: modelData.path ? theme.textColor : theme.mutedColor
                    }
                }
                Text {
                    visible: panel.decoding.status !== undefined
                    width: applications.width
                    wrapMode: Text.WordWrap
                    text: (panel.decoding.status === "ok" ? "✓  " : panel.decoding.status === "aucun" ? "!  " : "–  ")
                        + "Décodage vidéo matériel : " + panel.decoding.label
                        + (panel.decoding.hint ? " — " + panel.decoding.hint : "")
                    font.pixelSize: theme.fontBody
                    color: panel.decoding.status === "ok" ? theme.textColor
                         : panel.decoding.status === "aucun" ? theme.danger : theme.mutedColor
                }
                Item { width: 1; height: panel.associations.length ? 8 : 0 }
                Repeater {
                    model: panel.associations
                    delegate: Column {
                        required property var modelData
                        width: applications.width
                        Text {
                            width: parent.width
                            wrapMode: Text.WordWrap
                            text: (modelData.status === "ok" ? "✓  " : "!  ") + modelData.label + " s'ouvrent avec : " + modelData.current
                            font.pixelSize: theme.fontBody
                            color: modelData.status === "ok" ? theme.textColor : theme.danger
                        }
                        Text {
                            visible: modelData.status !== "ok"
                            leftPadding: 24
                            text: "Commande conseillée : " + modelData.fix
                            font.pixelSize: theme.fontSmall
                            font.family: "monospace"
                            color: theme.mutedColor
                        }
                    }
                }
            }

            // Maintenance --------------------------------------------------------
            Column {
                id: maintenance
                width: parent.width
                spacing: 16
                visible: panel.current === "maintenance"

                Text {
                    width: parent.width
                    wrapMode: Text.WordWrap
                    text: "Pour l'entretien de l'ordinateur. SigilDesk ne remplace pas le bureau LXQt : il se pose au-dessus."
                    font.pixelSize: theme.fontBody
                    color: theme.mutedColor
                }
                Text {
                    width: parent.width
                    wrapMode: Text.WordWrap
                    text: updates.autoUpdatesLabel + (updates.rebootRequired ? " Un redémarrage est nécessaire pour les terminer." : "")
                    font.pixelSize: theme.fontBody
                    color: updates.autoUpdatesEnabled ? theme.textColor : theme.danger
                }
                SdButton {
                    visible: updates.rebootRequired
                    kind: "primary"
                    text: "Redémarrer maintenant"
                    onClicked: app.reboot()
                }
                SdButton { text: "Afficher le bureau (réduire SigilDesk)"; onClicked: panel.minimizeRequested() }
                SdButton { text: "Quitter SigilDesk"; kind: "danger"; onClicked: panel.quitRequested() }
                Text {
                    width: parent.width
                    wrapMode: Text.WordWrap
                    text: "Raccourci clavier : " + app.maintenanceShortcut + " réduit SigilDesk.\n"
                        + "Pour revenir : menu des applications › SigilDesk."
                    font.pixelSize: theme.fontBody
                    color: theme.textColor
                    lineHeight: 1.25
                }
                Text {
                    visible: app.shortcutConflicts.length > 0
                    width: parent.width
                    wrapMode: Text.WordWrap
                    text: "Attention : ce raccourci est déjà utilisé par LXQt (" + app.shortcutConflicts.join(", ") + "). Changez-le dans le fichier de réglages."
                    font.pixelSize: theme.fontBody
                    color: theme.danger
                }
            }

            // À propos ------------------------------------------------------------
            Column {
                id: apropos
                width: parent.width
                spacing: 12
                visible: panel.current === "apropos"

                Text {
                    text: "SigilDesk · v" + app.version
                    font.pixelSize: theme.fontPanelTitle
                    font.weight: Font.DemiBold
                    color: theme.textColor
                }
                Text {
                    width: parent.width
                    wrapMode: Text.WordWrap
                    lineHeight: 1.2
                    text: "Un accueil simple, façon tablette, pour ouvrir en un clic Internet, vos mails, "
                        + "vos photos, vos vidéos et vos documents. SigilDesk se pose au-dessus du bureau "
                        + "de l'ordinateur sans rien y changer."
                    font.pixelSize: theme.fontBody
                    color: theme.textColor
                }
                Text {
                    width: parent.width
                    wrapMode: Text.WordWrap
                    text: app.copyright
                    font.pixelSize: theme.fontBody
                    font.weight: Font.DemiBold
                    color: theme.textColor
                }
                Text {
                    width: parent.width
                    wrapMode: Text.WordWrap
                    text: "Conçu et développé par " + app.author + " pour " + app.publisher + ". " + app.usage
                        + " Logiciel propriétaire : aucune copie ni diffusion sans accord écrit de " + app.publisher + "."
                    font.pixelSize: theme.fontBody
                    color: theme.mutedColor
                }
                SdButton {
                    objectName: "geo_about_site"
                    kind: "primary"
                    text: "Site : " + app.website.replace("https://", "").replace(/\/$/, "")
                    Accessible.description: "Ouvre " + app.website + " dans le navigateur"
                    onClicked: app.openLink(app.website)
                }
                Text {
                    width: parent.width
                    wrapMode: Text.WordWrap
                    topPadding: 6
                    text: weather.attribution + ". Composants Qt et PySide6 sous licence LGPL v3."
                    font.pixelSize: theme.fontSmall
                    color: theme.mutedColor
                }
                SdButton {
                    text: "open-meteo.com"
                    onClicked: app.openLink(weather.attributionUrl)
                }
                Repeater {
                    model: [
                        "Réglages : " + app.configPath,
                        "Journal : " + app.logPath,
                        "Icônes personnelles : " + app.iconsPath,
                        app.readOnlyConfig ? "Réglages en lecture seule (fichier d'une version plus récente)." : ""
                    ]
                    delegate: Text {
                        required property string modelData
                        visible: modelData !== ""
                        width: apropos.width
                        wrapMode: Text.WrapAnywhere
                        text: modelData
                        font.pixelSize: theme.fontSmall
                        color: theme.mutedColor
                    }
                }
            }
        }
    }
    ScrollHint { flick: page }
}
