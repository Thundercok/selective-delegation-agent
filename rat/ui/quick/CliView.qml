import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// CLI-to-UI: renders any rat.cli_views ViewSpec. Buttons run the argv they carry,
// dropped files are appended to the spec's drop_argv, refresh_seconds re-runs it.
ColumnLayout {
    id: cliView
    objectName: "cliView"
    readonly property var spec: desk.liveSnapshot.cliView || ({})
    readonly property var blocks: spec.blocks || []
    readonly property var dropArgv: {
        for (var i = 0; i < blocks.length; i++)
            if (blocks[i].type === "actions" && blocks[i].data.drop_argv) return blocks[i].data.drop_argv
        return null
    }
    readonly property int refreshSeconds: blocks.length && blocks[0].data.refresh_seconds ? blocks[0].data.refresh_seconds : 0
    visible: desk.liveMode && desk.liveSnapshot.view === "cli"
    Layout.fillWidth: true
    spacing: 8

    Timer {
        interval: Math.max(5, cliView.refreshSeconds) * 1000
        running: cliView.visible && cliView.refreshSeconds > 0 && !desk.liveSnapshot.cliBusy
        repeat: true
        onTriggered: desk.liveController.refreshCliView()
    }

    RowLayout {
        Layout.fillWidth: true
        Label {
            Layout.fillWidth: true
            text: "rat " + (desk.liveSnapshot.cliCommand || "")
            textFormat: Text.PlainText
            elide: Text.ElideRight
            color: desk.muted
            font.family: "Menlo"
            font.pixelSize: 11
        }
        QuietButton {
            objectName: "cliRefresh"
            text: "Chạy lại"
            font.pixelSize: 11
            enabled: !desk.liveSnapshot.cliBusy
            onClicked: desk.liveController.refreshCliView()
        }
        QuietButton {
            objectName: "cliClose"
            text: "Đóng"
            font.pixelSize: 11
            onClicked: desk.liveController.closeCliView()
        }
    }

    DeskProgress {
        visible: Boolean(desk.liveSnapshot.cliBusy)
        Layout.fillWidth: true
        indeterminate: true
    }

    Repeater {
        model: cliView.blocks
        delegate: ColumnLayout {
            id: block
            required property var modelData
            readonly property var info: modelData.data || ({})
            readonly property var headers: info.headers || info.table_headers || []
            readonly property var rows: info.rows || info.table_rows || []
            Layout.fillWidth: true
            spacing: 4

            // summary
            Rectangle {
                visible: block.modelData.type === "summary"
                Layout.fillWidth: true
                implicitHeight: summaryCol.implicitHeight + 20
                radius: desk.cardRadius
                color: desk.utilitySurface
                border.width: 1
                border.color: desk.edge
                ColumnLayout {
                    id: summaryCol
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: 10
                    spacing: 4
                    RowLayout {
                        Layout.fillWidth: true
                        Label {
                            Layout.fillWidth: true
                            text: block.info.title || ""
                            textFormat: Text.PlainText
                            wrapMode: Text.Wrap
                            color: desk.ink
                            font.pixelSize: 13
                            font.weight: Font.DemiBold
                        }
                        Label {
                            visible: Boolean(block.info.badge)
                            text: block.info.badge || ""
                            textFormat: Text.PlainText
                            color: desk.accent
                            font.pixelSize: 11
                        }
                    }
                    Label {
                        Layout.fillWidth: true
                        visible: text.length > 0
                        text: block.info.text || ""
                        textFormat: Text.PlainText
                        wrapMode: Text.Wrap
                        color: desk.ink
                        font.pixelSize: 12
                    }
                }
            }

            // table (and details carrying a table)
            Label {
                visible: block.headers.length > 0 && Boolean(block.info.title) && block.modelData.type !== "summary"
                text: block.info.title || ""
                textFormat: Text.PlainText
                color: desk.ink
                font.pixelSize: 12
                font.weight: Font.DemiBold
            }
            GridLayout {
                visible: block.headers.length > 0
                Layout.fillWidth: true
                columns: Math.max(1, block.headers.length)
                columnSpacing: 10
                rowSpacing: 3
                Repeater {
                    model: block.headers
                    Label {
                        required property var modelData
                        text: String(modelData)
                        textFormat: Text.PlainText
                        color: desk.muted
                        font.pixelSize: 11
                        font.weight: Font.DemiBold
                    }
                }
                Repeater {
                    model: block.headers.length ? [].concat.apply([], block.rows) : []
                    Label {
                        required property var modelData
                        Layout.fillWidth: true
                        Layout.maximumWidth: cliView.width / Math.max(1, block.headers.length) * 1.6
                        text: String(modelData)
                        textFormat: Text.PlainText
                        wrapMode: Text.Wrap
                        maximumLineCount: 6
                        elide: Text.ElideRight
                        color: desk.ink
                        font.pixelSize: 11
                    }
                }
            }

            // details text
            Label {
                visible: block.modelData.type === "details" && block.headers.length === 0
                Layout.fillWidth: true
                text: block.info.title || ""
                textFormat: Text.PlainText
                color: desk.ink
                font.pixelSize: 12
                font.weight: Font.DemiBold
            }
            TextArea {
                visible: block.modelData.type === "details" && block.headers.length === 0
                Layout.fillWidth: true
                readOnly: true
                selectByMouse: true
                wrapMode: TextEdit.Wrap
                text: String(block.info.content || "")
                textFormat: TextEdit.PlainText
                color: desk.ink
                font.family: "Menlo"
                font.pixelSize: 11
                background: Rectangle { radius: 6; color: desk.utilitySurface; border.color: desk.edge }
            }

            // actions: each command is the argv of the next view
            Flow {
                visible: block.modelData.type === "actions"
                Layout.fillWidth: true
                spacing: 6
                Repeater {
                    model: block.info.commands || []
                    QuietButton {
                        required property var modelData
                        text: modelData.label
                        primary: false
                        font.pixelSize: 12
                        enabled: !desk.liveSnapshot.cliBusy
                        onClicked: desk.liveController.runCliArgs(modelData.argv)
                    }
                }
            }
        }
    }

    Rectangle {
        objectName: "cliDropZone"
        visible: cliView.dropArgv !== null
        Layout.fillWidth: true
        implicitHeight: 54
        radius: desk.cardRadius
        color: cliDrop.containsDrag ? desk.utilitySurface : "transparent"
        border.width: 1
        border.color: cliDrop.containsDrag ? desk.accent : desk.edge
        Label {
            anchors.centerIn: parent
            text: "Thả PDF vào đây"
            textFormat: Text.PlainText
            color: desk.muted
            font.pixelSize: 12
        }
        DropArea {
            id: cliDrop
            anchors.fill: parent
            onDropped: (drop) => {
                if (drop.hasUrls && cliView.dropArgv) {
                    desk.liveController.runCliDrop(cliView.dropArgv, drop.urls)
                    drop.accept()
                }
            }
        }
    }
}
