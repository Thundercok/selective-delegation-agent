import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: answerView
    property alias answerText: answerText
    visible: desk.liveMode && desk.liveSnapshot.view === "answer"
    Layout.fillWidth: true
    spacing: desk.emptyCancelledAnswer ? 8 : 12

                    ColumnLayout {
                        visible: desk.liveSnapshot.view === "answer"
                        Layout.fillWidth: true
                        spacing: 4

                        // The question, as one quiet line: the user just typed it.
                        Item {
                            id: answerQuestionCard
                            objectName: "answerQuestionCard"
                            Layout.fillWidth: true
                            implicitHeight: answerQuestion.implicitHeight

                            Button {
                                id: answerQuestion
                                objectName: "answerQuestion"
                                anchors.left: parent.left
                                anchors.right: parent.right
                                padding: 0
                                hoverEnabled: true
                                Accessible.name: "Câu hỏi: " + (desk.liveSnapshot.userQuery || "")
                                Accessible.description: "Mở hoặc thu câu hỏi đầy đủ"
                                onClicked: desk.answerQuestionOpen = !desk.answerQuestionOpen
                                rightPadding: questionChevron.visible ? 16 : 0
                                contentItem: Label {
                                    text: desk.liveSnapshot.userQuery || ""
                                    textFormat: Text.PlainText
                                    font.pixelSize: 13
                                    color: desk.muted
                                    wrapMode: desk.answerQuestionOpen ? Text.Wrap : Text.NoWrap
                                    elide: desk.answerQuestionOpen ? Text.ElideNone : Text.ElideRight
                                    font.underline: answerQuestion.visualFocus
                                }
                                background: Item {}
                                ToolTip.delay: 600
                                ToolTip.visible: hovered && !desk.answerQuestionOpen && (desk.liveSnapshot.userQuery || "").length > 48
                                ToolTip.text: desk.liveSnapshot.userQuery || ""
                            }
                            DeskIcon {
                                id: questionChevron
                                visible: (desk.liveSnapshot.userQuery || "").length > 48
                                name: desk.answerQuestionOpen ? "chevron-up" : "chevron-down"
                                color: desk.muted
                                anchors.right: parent.right
                                anchors.top: parent.top
                                anchors.topMargin: 3
                                width: 12
                                height: 12
                            }
                        }

                        // One meta row: where the answer comes from, whether it was checked, and the
                        // way into how it was found. The step chain lives behind "Chi tiết".
                        Item {
                            id: evidenceProcessCard
                            objectName: "evidenceProcessCard"
                            Layout.fillWidth: true
                            implicitHeight: evidenceProcessCol.implicitHeight

                            ColumnLayout {
                                id: evidenceProcessCol
                                anchors.left: parent.left
                                anchors.right: parent.right
                                spacing: 6

                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: 6

                                    DeskIcon {
                                        visible: answerDocumentLabel.visible
                                        name: "file"
                                        color: desk.accent
                                        width: 12
                                        height: 12
                                        Layout.preferredWidth: 12
                                        Layout.preferredHeight: 12
                                    }
                                    Label {
                                        id: answerDocumentLabel
                                        objectName: "answerDocumentLabel"
                                        visible: Boolean(text)
                                        text: {
                                            if (desk.liveSnapshot.answerSources && desk.liveSnapshot.answerSources.length > 0 && desk.liveSnapshot.answerSources[0].title) {
                                                return desk.liveSnapshot.answerSources[0].title
                                            }
                                            return desk.liveSnapshot.fileName || ""
                                        }
                                        font.pixelSize: 12
                                        font.weight: Font.Medium
                                        color: desk.accent
                                        elide: Text.ElideMiddle
                                        Layout.fillWidth: true
                                        Layout.maximumWidth: implicitWidth
                                        HoverHandler { id: docLabelHover }
                                        ToolTip.visible: docLabelHover.hovered && truncated
                                        ToolTip.text: answerDocumentLabel.text
                                    }
                                    Rectangle {
                                        id: answerVerificationBadge
                                        objectName: "answerVerificationBadge"
                                        readonly property string state: desk.liveSnapshot.answerVerification || "UNKNOWN"
                                        radius: 4
                                        color: state === "FAIL" ? Qt.rgba(desk.warningInk.r, desk.warningInk.g, desk.warningInk.b, 0.14)
                                             : state === "PASS" ? desk.selectedSurface : "transparent"
                                        border.width: 1
                                        border.color: state === "FAIL" ? desk.warningInk : state === "PASS" ? desk.selectedEdge : desk.edge
                                        implicitWidth: verifBadgeLabel.implicitWidth + 10
                                        implicitHeight: 18
                                        Label {
                                            id: verifBadgeLabel
                                            anchors.centerIn: parent
                                            text: answerVerificationBadge.state === "PASS" ? "Đã đối chiếu nguồn"
                                                : answerVerificationBadge.state === "FAIL" ? "Chưa khớp nguồn" : "Chưa xác minh"
                                            font.pixelSize: 11
                                            font.weight: Font.Medium
                                            color: answerVerificationBadge.state === "FAIL" ? desk.warningInk
                                                 : answerVerificationBadge.state === "PASS" ? desk.accent : desk.muted
                                        }
                                        Accessible.role: Accessible.StaticText
                                        Accessible.name: verifBadgeLabel.text
                                        Accessible.description: state === "FAIL"
                                            ? "Bước kiểm tra báo câu trả lời chưa khớp với nguồn. Hãy mở nguồn để đối chiếu."
                                            : (state !== "PASS" ? "Chưa có bước kiểm tra nào xác nhận câu trả lời này. Hãy mở nguồn để tự đối chiếu." : "")
                                        HoverHandler { id: verificationHover }
                                        ToolTip.visible: verificationHover.hovered && state !== "PASS"
                                        ToolTip.delay: 600
                                        ToolTip.text: Accessible.description
                                    }

                                    Item { Layout.fillWidth: true }

                                    QuietButton {
                                        id: processDetailsToggle
                                        objectName: "processDetailsToggle"
                                        text: evidenceProcessCard.width < 340 ? "" : "Cách tìm"
                                        trailingIconName: desk.processDetailsOpen ? "chevron-up" : "chevron-down"
                                        trailingIconSize: 10
                                        topPadding: 2
                                        bottomPadding: 2
                                        leftPadding: 4
                                        rightPadding: 4
                                        font.pixelSize: 11
                                        Accessible.name: (desk.processDetailsOpen ? "Thu gọn" : "Xem") + " chi tiết đối chiếu"
                                        Accessible.role: Accessible.Button
                                        checkable: true
                                        checked: desk.processDetailsOpen
                                        onClicked: desk.processDetailsOpen = !desk.processDetailsOpen
                                    }
                                }

                                ColumnLayout {
                                    id: processDetailsContent
                                    objectName: "processDetailsContent"
                                    visible: desk.processDetailsOpen
                                    Layout.fillWidth: true
                                    spacing: 4

                                    Rectangle { Layout.fillWidth: true; height: 1; color: desk.edge; opacity: 0.6 }

                                    Flow {
                                        visible: processStepsRepeater.count > 0
                                        Layout.fillWidth: true
                                        spacing: 4

                                        Repeater {
                                            id: processStepsRepeater
                                            objectName: "processStepsRepeater"
                                            model: desk.liveSnapshot.processSteps || []

                                            Row {
                                                spacing: 4
                                                Rectangle {
                                                    radius: 4
                                                    color: (modelData.status === "verified_fail") ? Qt.rgba(desk.warningInk.r, desk.warningInk.g, desk.warningInk.b, 0.14) :
                                                           (modelData.status === "unverified") ? desk.utilitySurface :
                                                           desk.selectedSurface
                                                    border.width: 1
                                                    border.color: (modelData.status === "verified_fail") ? desk.warningInk :
                                                                  (modelData.status === "unverified") ? desk.edge :
                                                                  desk.selectedEdge
                                                    height: 20
                                                    width: chipInnerRow.implicitWidth + 8
                                                    RowLayout {
                                                        id: chipInnerRow
                                                        anchors.centerIn: parent
                                                        spacing: 3
                                                        DeskIcon {
                                                            name: modelData.iconName || "check"
                                                            color: (modelData.status === "verified_fail") ? desk.warningInk :
                                                                   (modelData.status === "unverified") ? desk.muted :
                                                                   desk.accent
                                                            width: 10
                                                            height: 10
                                                            Layout.preferredWidth: 10
                                                            Layout.preferredHeight: 10
                                                        }
                                                        Label {
                                                            text: modelData.fullTitle || modelData.shortTitle || ""
                                                            font.pixelSize: 11
                                                            font.weight: Font.Medium
                                                            color: (modelData.status === "verified_fail") ? desk.warningInk :
                                                                   (modelData.status === "unverified") ? desk.muted :
                                                                   desk.accent
                                                        }
                                                    }
                                                }
                                                Label {
                                                    visible: index < (processStepsRepeater.count - 1)
                                                    text: "→"
                                                    color: desk.muted
                                                    font.pixelSize: 11
                                                    height: 20
                                                    verticalAlignment: Text.AlignVCenter
                                                }
                                            }
                                        }
                                    }

                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: 6
                                        Label {
                                            text: "Phạm vi đọc:"
                                            font.pixelSize: 12
                                            font.weight: Font.Medium
                                            color: desk.muted
                                        }
                                        Label {
                                            text: desk.liveSnapshot.answerReadScope || (desk.liveSnapshot.fileName ? desk.liveSnapshot.fileName + " · Toàn văn / Đoạn trích" : "Tài liệu được chọn")
                                            font.pixelSize: 12
                                            color: desk.ink
                                            Layout.fillWidth: true
                                            elide: Text.ElideRight
                                        }
                                    }

                                    Repeater {
                                        model: desk.liveSnapshot.processSteps || []
                                        ColumnLayout {
                                            Layout.fillWidth: true
                                            spacing: 2
                                            visible: Boolean(modelData.detail || modelData.thought)
                                            RowLayout {
                                                Layout.fillWidth: true
                                                spacing: 6
                                                Label {
                                                    text: (modelData.shortTitle || "Bước") + ":"
                                                    font.pixelSize: 12
                                                    font.weight: Font.Medium
                                                    color: desk.muted
                                                }
                                                Label {
                                                    text: modelData.detail || ""
                                                    font.pixelSize: 12
                                                    color: desk.ink
                                                    Layout.fillWidth: true
                                                    elide: Text.ElideRight
                                                }
                                            }
                                            Label {
                                                visible: Boolean(modelData.thought)
                                                text: modelData.thought || ""
                                                font.pixelSize: 12
                                                font.italic: true
                                                color: desk.muted
                                                Layout.fillWidth: true
                                                wrapMode: Text.Wrap
                                                leftPadding: 12
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                    ArtifactCard {
                        id: answerArtifactCard
                        objectName: "answerArtifactCard"
                        visible: desk.liveSnapshot.view === "answer" && !desk.emptyCancelledAnswer && Boolean(desk.liveSnapshot.artifactCard && desk.liveSnapshot.artifactCard.visual_type)
                        cardData: desk.liveSnapshot.artifactCard || ({})
                        Layout.fillWidth: true
                    }
                    TextArea {
                        id: answerText
                        objectName: "answerText"
                        visible: desk.liveSnapshot.view === "answer" && !desk.emptyCancelledAnswer
                        Layout.fillWidth: true
                        Layout.preferredHeight: contentHeight
                        text: desk.displayedAnswerHtml
                        textFormat: TextEdit.RichText
                        wrapMode: TextEdit.Wrap
                        readOnly: true
                        selectByMouse: true
                        persistentSelection: true
                        color: desk.ink
                        selectionColor: desk.accent
                        selectedTextColor: desk.accentText
                        font.pixelSize: 14
                        padding: 0
                        background: null
                        Accessible.name: "Câu trả lời của trợ lý"
                    }
                    Rectangle {
                        id: evidenceSourceCard
                        objectName: "evidenceSourceCard"
                        readonly property bool hasSnippet: Boolean((desk.liveSnapshot.answerSources || []).length > 0 && desk.liveSnapshot.answerSources[0].snippet)
                        visible: desk.liveSnapshot.view === "answer" && !desk.emptyCancelledAnswer && (desk.liveSnapshot.answerSources || []).length > 0
                        Layout.fillWidth: true
                        implicitHeight: evidenceSourceCol.implicitHeight + 18
                        radius: desk.cardRadius
                        color: desk.utilitySurface
                        border.width: 1
                        border.color: desk.edge

                        ColumnLayout {
                            id: evidenceSourceCol
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.top: parent.top
                            anchors.leftMargin: 12
                            anchors.rightMargin: 12
                            anchors.topMargin: 10
                            spacing: 8

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 6

                                DeskIcon { name: "file"; color: desk.accent; width: 13; height: 13; Layout.preferredWidth: 13; Layout.preferredHeight: 13 }

                                Label {
                                    id: evidenceSourceTitle
                                    objectName: "evidenceSourceTitle"
                                    text: {
                                        if (desk.liveSnapshot.answerSources && desk.liveSnapshot.answerSources.length > 0) {
                                            const s = desk.liveSnapshot.answerSources[0]
                                            return "Nguồn: " + (s.title || desk.liveSnapshot.fileName || "Tài liệu") + (s.page > 0 ? (" · Trang " + s.page) : "") + (s.section ? (" · " + s.section) : "")
                                        }
                                        return "Nguồn: " + (desk.liveSnapshot.fileName || "")
                                    }
                                    font.pixelSize: 12
                                    font.weight: Font.Medium
                                    color: desk.ink
                                    elide: Text.ElideMiddle
                                    Layout.fillWidth: true
                                }

                                QuietButton {
                                    id: expandContextButton
                                    objectName: "expandContextButton"
                                    text: resultPaper.width < 520 ? "" : (desk.contextExpanded ? "Thu gọn" : (resultPaper.width < 620 ? "+ Ngữ cảnh" : "Mở rộng ngữ cảnh"))
                                    iconName: desk.contextExpanded ? "minus" : "plus"
                                    iconSize: 11
                                    topPadding: 3
                                    bottomPadding: 3
                                    leftPadding: resultPaper.width < 520 ? 4 : 6
                                    rightPadding: resultPaper.width < 520 ? 4 : 6
                                    font.pixelSize: 12
                                    Accessible.name: desk.contextExpanded ? "Thu gọn về đoạn trích ngắn" : "Mở rộng ngữ cảnh xung quanh đoạn trích"
                                    Accessible.role: Accessible.Button
                                    ToolTip.visible: hovered
                                    ToolTip.text: desk.contextExpanded ? "Thu gọn về đoạn trích ngắn" : "Mở rộng ngữ cảnh xung quanh đoạn trích"
                                    onClicked: {
                                        if (!desk.contextExpanded && desk.liveController)
                                            desk.expandedEvidenceText = desk.liveController.getExpandedContext(0)
                                        desk.contextExpanded = !desk.contextExpanded
                                    }
                                }

                                QuietButton {
                                    id: copyCitationButton
                                    objectName: "copyCitationButton"
                                    text: resultPaper.width < 520 ? "" : (desk.sourceCopied ? "Đã chép" : (resultPaper.width < 620 ? "Chép" : "Chép trích dẫn"))
                                    iconName: desk.sourceCopied ? "check" : "copy"
                                    iconSize: 11
                                    topPadding: 3
                                    bottomPadding: 3
                                    leftPadding: resultPaper.width < 520 ? 4 : 6
                                    rightPadding: resultPaper.width < 520 ? 4 : 6
                                    font.pixelSize: 12
                                    Accessible.name: "Sao chép trích dẫn và nguồn"
                                    Accessible.role: Accessible.Button
                                    ToolTip.visible: hovered
                                    ToolTip.text: desk.sourceCopied ? "Đã sao chép vào bộ nhớ tạm" : "Sao chép trích dẫn và nguồn"
                                    onClicked: {
                                        const citation = evidenceSourceSnippet.text + (evidenceSourceTitle.text ? ("\n\n— " + evidenceSourceTitle.text) : "")
                                        if (desk.liveController.copyCitation(citation)) {
                                            desk.sourceCopied = true
                                            sourceCopyFeedback.restart()
                                        }
                                    }
                                }

                                QuietButton {
                                    id: openExternalPdfButton
                                    objectName: "openExternalPdfButton"
                                    text: resultPaper.width < 520 ? "" : (resultPaper.width < 620 ? "Mở PDF" : "Mở PDF gốc")
                                    iconName: resultPaper.width < 520 ? "external" : ""
                                    trailingIconName: resultPaper.width < 520 ? "" : "external"
                                    iconSize: 11
                                    trailingIconSize: 11
                                    topPadding: 3
                                    bottomPadding: 3
                                    leftPadding: resultPaper.width < 520 ? 4 : 6
                                    rightPadding: resultPaper.width < 520 ? 4 : 6
                                    font.pixelSize: 12
                                    Accessible.name: "Mở tài liệu bằng ứng dụng PDF bên ngoài"
                                    Accessible.role: Accessible.Button
                                    ToolTip.visible: hovered
                                    ToolTip.text: "Mở tài liệu bằng ứng dụng PDF bên ngoài"
                                    onClicked: desk.liveController.openOriginal()
                                }
                            }

                            Rectangle { visible: evidenceSourceCard.hasSnippet || desk.contextExpanded; Layout.fillWidth: true; height: 1; color: desk.edge; opacity: 0.6 }

                            RowLayout {
                                visible: evidenceSourceCard.hasSnippet || desk.contextExpanded
                                Layout.fillWidth: true
                                spacing: 8

                                Rectangle {
                                    Layout.preferredWidth: 3
                                    Layout.fillHeight: true
                                    radius: 1.5
                                    color: desk.accent
                                    opacity: 0.8
                                }

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 4

                                    Rectangle {
                                        visible: desk.contextExpanded
                                        radius: 4
                                        color: desk.selectedSurface
                                        border.width: 1
                                        border.color: desk.selectedEdge
                                        implicitHeight: 18
                                        implicitWidth: expandedTagLabel.implicitWidth + 8
                                        Label {
                                            id: expandedTagLabel
                                            anchors.centerIn: parent
                                            text: "Ngữ cảnh mở rộng"
                                            font.pixelSize: 11
                                            font.weight: Font.Medium
                                            color: desk.accent
                                        }
                                    }

                                    Label {
                                        id: evidenceSourceSnippet
                                        objectName: "evidenceSourceSnippet"
                                        Layout.fillWidth: true
                                        text: {
                                            var raw = "Chưa có đoạn nguồn cho tham chiếu này."
                                            if (desk.liveSnapshot.answerSources && desk.liveSnapshot.answerSources.length > 0) {
                                                const s = desk.liveSnapshot.answerSources[0]
                                                if (desk.contextExpanded) {
                                                    if (s.extendedSnippet && s.extendedSnippet.length > (s.snippet || "").length) {
                                                        raw = s.extendedSnippet
                                                    } else if (desk.expandedEvidenceText) {
                                                        raw = desk.expandedEvidenceText
                                                    } else {
                                                        raw = s.snippet || raw
                                                    }
                                                } else {
                                                    raw = s.snippet || raw
                                                }
                                            }
                                            return desk.cleanSnippetText(raw)
                                        }
                                        font.pixelSize: 12
                                        lineHeight: 1.3
                                        color: desk.ink
                                        wrapMode: Text.Wrap
                                        textFormat: Text.PlainText
                                    }
                                }
                            }
                        }
                    }
                    ColumnLayout {
                        id: answerReferences
                        objectName: "answerReferences"
                        visible: desk.liveSnapshot.view === "answer" && !desk.emptyCancelledAnswer && (desk.liveSnapshot.answerSources || []).length > 0
                        Layout.fillWidth: true
                        spacing: 8
                        Item { Layout.preferredHeight: 4 }
                        Rectangle { Layout.fillWidth: true; height: 1; color: desk.edge }
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 6
                            QuietButton {
                                objectName: "answerSourcesToggle"
                                visible: (desk.liveSnapshot.answerSources || []).length > 0
                                text: (desk.liveSnapshot.answerSources || []).length + " tham chiếu"
                                iconName: desk.answerSourcesOpen ? "chevron-down" : "chevron-right"
                                iconSize: 13
                                leftPadding: 0
                                topPadding: 4
                                bottomPadding: 4
                                Accessible.name: (desk.answerSourcesOpen ? "Thu" : "Mở") + " tham chiếu của lượt trả lời"
                                Accessible.role: Accessible.Button
                                checkable: true
                                checked: desk.answerSourcesOpen
                                onClicked: desk.answerSourcesOpen = !desk.answerSourcesOpen
                            }
                        }
                        ColumnLayout {
                            visible: desk.answerSourcesOpen
                            Layout.fillWidth: true
                            spacing: 8
                            Repeater {
                                model: desk.liveSnapshot.view === "answer" ? (desk.liveSnapshot.answerSources || []) : []
                                ColumnLayout {
                                    required property var modelData
                                    required property int index
                                    Layout.fillWidth: true
                                    spacing: 6
                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: 8
                                        DeskIcon { name: "file"; color: desk.muted; Layout.preferredWidth: 14; Layout.preferredHeight: 14 }
                                        Label {
                                            text: modelData.title + (modelData.readScope ? " · " + modelData.readScope : "")
                                            textFormat: Text.PlainText
                                            font.pixelSize: 12
                                            color: desk.muted
                                            wrapMode: Text.Wrap
                                            Layout.fillWidth: true
                                        }
                                        QuietButton {
                                            objectName: "openAnswerSource_" + index
                                            visible: true
                                            enabled: Boolean(modelData.canOpen)
                                            text: modelData.label || (modelData.page > 0 ? ("Trang " + modelData.page) : "Chưa xác định trang")
                                            Accessible.name: (modelData.canOpen ? "Đọc trang " : "Tham chiếu: ") + text + ", " + modelData.title
                                            topPadding: 4
                                            bottomPadding: 4
                                            onClicked: {
                                                if (modelData.canOpen) {
                                                    if (desk.isSideBySidePdfActive) {
                                                        desk.liveController.previewPdfPageWithSnippet(modelData.page, modelData.snippet || "")
                                                    } else {
                                                        desk.liveController.openAnswerSource(index)
                                                    }
                                                }
                                            }
                                        }
                                    }
                                    PdfSnapshotCard {
                                        objectName: "sourceSnapshot_" + index
                                        activeSnapshot: desk.answerSourcesOpen && Boolean(modelData.canOpen)
                                        pdfPath: modelData.path || ""
                                        pdfPage: modelData.page || 0
                                        matchQuery: ""
                                        matchSnippet: modelData.snippet || ""
                                        maxCardHeight: 108
                                        Accessible.name: "Ảnh chụp tham chiếu trang PDF " + modelData.page + ", bấm để đọc trang"
                                        onActivated: {
                                            if (desk.isSideBySidePdfActive) {
                                                desk.liveController.previewPdfPageWithSnippet(modelData.page, modelData.snippet || "")
                                            } else {
                                                desk.liveController.openAnswerSource(index)
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }

}
