import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: cardRoot
    property var cardData: ({})
    readonly property string visualType: cardData ? (cardData.visual_type || "") : ""

    Accessible.role: Accessible.Grouping
    Accessible.name: {
        if (visualType === "iching") return "Quẻ Kinh Dịch: " + (cardData ? (cardData.hexagram_name || "") : "")
        if (visualType === "natal") return "Lá số Chiêm tinh: " + (cardData ? (cardData.chart_title || "") : "")
        if (visualType === "timetable") return "Lịch học và thời khóa biểu"
        if (visualType === "web_preview") return "Xem trước trang web: " + (cardData ? (cardData.title || "") : "")
        return "Thẻ thông tin trực quan"
    }
    Accessible.description: cardData ? (cardData.summary || cardData.interpretation || cardData.description || "") : ""

    visible: visualType !== ""
    implicitHeight: contentCol.implicitHeight + 24
    radius: 12
    color: desk.utilitySurface
    border.width: 1
    border.color: desk.edge

    ColumnLayout {
        id: contentCol
        anchors.fill: parent
        anchors.margins: 14
        spacing: 12

        // --- 1. KINH DỊCH (I CHING) ---
        ColumnLayout {
            visible: cardRoot.visualType === "iching"
            Layout.fillWidth: true
            spacing: 10

            // Header Tag
            RowLayout {
                spacing: 8
                Badge {
                    text: "🔮 QUẺ KINH DỊCH"
                    textColor: desk.accent
                    fontWeight: Font.DemiBold
                    color: Qt.rgba(desk.accent.r, desk.accent.g, desk.accent.b, 0.15)
                }
                Label {
                    text: cardRoot.cardData ? (cardRoot.cardData.question || "") : ""
                    font.pixelSize: 12
                    color: desk.muted
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                }
            }

            // Hexagram Visual + Description Row
            RowLayout {
                Layout.fillWidth: true
                spacing: 16

                // 6 Yin/Yang Lines (Drawn from Line 6 down to Line 1)
                Rectangle {
                    implicitWidth: 120
                    implicitHeight: 88
                    radius: 8
                    color: desk.inputColor
                    border.width: 1
                    border.color: desk.edge

                    ColumnLayout {
                        anchors.centerIn: parent
                        spacing: 5
                        Repeater {
                            // lines array is 0..5 (line 1 is index 0, line 6 is index 5).
                            // Display top to bottom: index 5 down to 0.
                            model: 6
                            Item {
                                readonly property int lineNum: 6 - index // 6, 5, 4, 3, 2, 1
                                readonly property int lineIdx: lineNum - 1
                                readonly property var rawLines: cardRoot.cardData && cardRoot.cardData.lines ? cardRoot.cardData.lines : [1,1,1,1,1,1]
                                readonly property int isYang: lineIdx < rawLines.length ? rawLines[lineIdx] : 1
                                readonly property var changingList: cardRoot.cardData && cardRoot.cardData.changing_lines ? cardRoot.cardData.changing_lines : []
                                readonly property bool isChanging: changingList.indexOf(lineNum) !== -1

                                implicitWidth: 92
                                implicitHeight: 7

                                RowLayout {
                                    anchors.centerIn: parent
                                    spacing: 8
                                    visible: isYang === 0 // Yin (2 broken bars)
                                    Rectangle {
                                        width: 40; height: 6; radius: 3
                                        color: isChanging ? desk.warningInk : desk.accent
                                    }
                                    Rectangle {
                                        width: 40; height: 6; radius: 3
                                        color: isChanging ? desk.warningInk : desk.accent
                                    }
                                }
                                Rectangle {
                                    anchors.centerIn: parent
                                    visible: isYang === 1 // Yang (1 solid bar)
                                    width: 88; height: 6; radius: 3
                                    color: isChanging ? desk.warningInk : desk.accent
                                }
                            }
                        }
                    }
                }

                // Hexagram Details
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 4

                    Label {
                        text: cardRoot.cardData ? (cardRoot.cardData.hexagram_name || "") : ""
                        font.pixelSize: 18
                        font.weight: Font.DemiBold
                        color: desk.ink
                    }
                    Label {
                        text: cardRoot.cardData ? ("Thượng: " + (cardRoot.cardData.upper_trigram || "") + " · Hạ: " + (cardRoot.cardData.lower_trigram || "")) : ""
                        font.pixelSize: 12
                        color: desk.muted
                    }
                    Label {
                        text: cardRoot.cardData ? (cardRoot.cardData.meaning || "") : ""
                        font.pixelSize: 12
                        color: desk.ink
                        wrapMode: Text.Wrap
                        Layout.fillWidth: true
                    }
                }
            }

            // Chuột's Advice Pill
            Rectangle {
                visible: Boolean(cardRoot.cardData && cardRoot.cardData.advice)
                Layout.fillWidth: true
                radius: 8
                color: desk.inputColor
                border.width: 1
                border.color: desk.edge
                implicitHeight: adviceText.implicitHeight + 14

                RowLayout {
                    anchors.fill: parent
                    anchors.margins: 8
                    spacing: 8
                    Label { text: "💡"; font.pixelSize: 14 }
                    Label {
                        id: adviceText
                        text: cardRoot.cardData ? (cardRoot.cardData.advice || "") : ""
                        font.pixelSize: 12
                        color: desk.ink
                        wrapMode: Text.Wrap
                        Layout.fillWidth: true
                    }
                }
            }
        }

        // --- 2. LENORMAND ORACLE (3 CARDS) ---
        ColumnLayout {
            visible: cardRoot.visualType === "lenormand"
            Layout.fillWidth: true
            spacing: 10

            // Header Tag
            RowLayout {
                spacing: 8
                Badge {
                    text: "🃏 BÀI LENORMAND"
                    textColor: desk.accent
                    fontWeight: Font.DemiBold
                    color: Qt.rgba(desk.accent.r, desk.accent.g, desk.accent.b, 0.15)
                }
                Label {
                    text: cardRoot.cardData ? (cardRoot.cardData.question || "Trải bài 3 lá") : ""
                    font.pixelSize: 12
                    color: desk.muted
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                }
            }

            // 3 Card Spread Row
            RowLayout {
                Layout.fillWidth: true
                spacing: 8

                Repeater {
                    model: cardRoot.cardData && cardRoot.cardData.cards ? cardRoot.cardData.cards : []
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredWidth: 1
                        implicitHeight: 124
                        radius: 8
                        color: desk.inputColor
                        border.width: 1
                        border.color: desk.edge

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 8
                            spacing: 3

                            // Slot Label (Past/Present/Future)
                            Label {
                                text: (modelData.slot || "").toUpperCase()
                                font.pixelSize: 11
                                font.weight: Font.DemiBold
                                color: desk.muted
                                elide: Text.ElideRight
                                Layout.fillWidth: true
                            }

                            // Card Emoji Icon
                            Label {
                                text: modelData.icon || "🎴"
                                font.pixelSize: 24
                                Layout.alignment: Qt.AlignHCenter
                            }

                            // Card Name
                            Label {
                                text: modelData.name || ""
                                font.pixelSize: 12
                                font.weight: Font.DemiBold
                                color: desk.ink
                                elide: Text.ElideRight
                                Layout.alignment: Qt.AlignHCenter
                            }

                            // Meaning
                            Label {
                                text: modelData.meaning || ""
                                font.pixelSize: 11
                                color: desk.muted
                                wrapMode: Text.Wrap
                                elide: Text.ElideRight
                                maximumLineCount: 2
                                Layout.fillWidth: true
                            }
                        }
                    }
                }
            }
        }

        // --- 3. THỜI KHÓA BIỂU (TIMETABLE) ---
        ColumnLayout {
            visible: cardRoot.visualType === "timetable"
            Layout.fillWidth: true
            spacing: 10

            // Header Tag
            RowLayout {
                spacing: 8
                Badge {
                    text: "📅 THỜI KHÓA BIỂU"
                    textColor: desk.accent
                    fontWeight: Font.DemiBold
                    color: Qt.rgba(desk.accent.r, desk.accent.g, desk.accent.b, 0.15)
                }
                Label {
                    text: cardRoot.cardData ? (cardRoot.cardData.day || "Hôm nay") : ""
                    font.pixelSize: 12
                    font.weight: Font.Medium
                    color: desk.ink
                }
                Item { Layout.fillWidth: true }
                Label {
                    text: cardRoot.cardData && cardRoot.cardData.sessions ? (cardRoot.cardData.sessions.length + " môn học") : ""
                    font.pixelSize: 12
                    color: desk.muted
                }
            }

            // Sessions List
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 6

                Repeater {
                    model: cardRoot.cardData && cardRoot.cardData.sessions ? cardRoot.cardData.sessions : []
                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: 46
                        radius: 8
                        color: desk.inputColor
                        border.width: 1
                        border.color: desk.edge

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 10
                            anchors.rightMargin: 10
                            spacing: 10

                            // Time Badge
                            Badge {
                                text: modelData.time || ""
                                textColor: desk.accentText
                                fontWeight: Font.DemiBold
                                color: desk.accent
                            }

                            // Room Badge
                            Badge {
                                text: modelData.room ? ("Phòng " + modelData.room) : "Chưa rõ phòng"
                                textColor: desk.ink
                            }

                            // Course Name & Instructor
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 1
                                Label {
                                    text: modelData.course_name || ""
                                    font.pixelSize: 12
                                    font.weight: Font.Medium
                                    color: desk.ink
                                    elide: Text.ElideRight
                                    Layout.fillWidth: true
                                }
                                Label {
                                    text: modelData.instructor ? ("GV: " + modelData.instructor) : ""
                                    font.pixelSize: 11
                                    color: desk.muted
                                    visible: Boolean(modelData.instructor)
                                }
                            }
                        }
                    }
                }

                Label {
                    visible: cardRoot.cardData && (!cardRoot.cardData.sessions || cardRoot.cardData.sessions.length === 0)
                    text: "🎉 Không có tiết học nào trong ngày này. Bạn được nghỉ!"
                    font.pixelSize: 12
                    color: desk.muted
                    Layout.alignment: Qt.AlignHCenter
                }
            }
        }

        // --- 4. WEB READER SUMMARY ---
        ColumnLayout {
            visible: cardRoot.visualType === "web"
            Layout.fillWidth: true
            spacing: 8

            // Header Tag
            RowLayout {
                spacing: 8
                Badge {
                    text: "🌐 TRANG WEB"
                    textColor: desk.accent
                    fontWeight: Font.DemiBold
                    color: Qt.rgba(desk.accent.r, desk.accent.g, desk.accent.b, 0.15)
                }
                Rectangle {
                    visible: Boolean(cardRoot.cardData && cardRoot.cardData.domain)
                    radius: 4
                    color: desk.selectedSurface
                    border.width: 1
                    border.color: desk.selectedEdge
                    implicitWidth: domLbl.implicitWidth + 8
                    implicitHeight: 20
                    Label {
                        id: domLbl
                        anchors.centerIn: parent
                        text: cardRoot.cardData ? (cardRoot.cardData.domain || "") : ""
                        font.pixelSize: 11
                        color: desk.accent
                    }
                }
                Item { Layout.fillWidth: true }
                QuietButton {
                    text: "Mở web"
                    plain: true
                    font.pixelSize: 12
                    visible: Boolean(cardRoot.cardData && cardRoot.cardData.url)
                    onClicked: {
                        if (cardRoot.cardData && cardRoot.cardData.url) {
                            Qt.openUrlExternally(cardRoot.cardData.url)
                        }
                    }
                }
            }

            // Title
            Label {
                text: cardRoot.cardData ? (cardRoot.cardData.title || "") : ""
                font.pixelSize: 14
                font.weight: Font.DemiBold
                color: desk.ink
                wrapMode: Text.Wrap
                Layout.fillWidth: true
            }

            // Bullets
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 5
                Repeater {
                    model: cardRoot.cardData && cardRoot.cardData.bullets ? cardRoot.cardData.bullets : []
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8
                        Label {
                            text: "•"
                            font.pixelSize: 14
                            color: desk.accent
                            Layout.alignment: Qt.AlignTop
                        }
                        Label {
                            text: modelData
                            font.pixelSize: 12
                            color: desk.ink
                            wrapMode: Text.Wrap
                            Layout.fillWidth: true
                        }
                    }
                }
            }
        }

        // --- 5. BẢNG DỮ LIỆU / DASHBOARD (TABLE) ---
        ColumnLayout {
            visible: cardRoot.visualType === "table"
            Layout.fillWidth: true
            spacing: 10

            RowLayout {
                spacing: 8
                Badge {
                    text: "📊 BẢNG TỔNG HỢP"
                    textColor: desk.accent
                    fontWeight: Font.DemiBold
                    color: Qt.rgba(desk.accent.r, desk.accent.g, desk.accent.b, 0.15)
                }
                Label {
                    text: cardRoot.cardData ? (cardRoot.cardData.title || "") : ""
                    font.pixelSize: 13
                    font.weight: Font.DemiBold
                    color: desk.ink
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 6

                Repeater {
                    model: cardRoot.cardData && cardRoot.cardData.rows ? cardRoot.cardData.rows : []
                    delegate: Rectangle {
                        id: tableRowCard
                        required property var modelData
                        readonly property var headersList: cardRoot.cardData && cardRoot.cardData.headers ? cardRoot.cardData.headers : []
                        readonly property var cellItems: {
                            const r = modelData
                            const hl = headersList || []
                            const hlLen = (typeof hl.length === "number") ? hl.length : 0
                            if (r && typeof r !== "string" && typeof r.length === "number") {
                                const out = []
                                for (let idx = 0; idx < r.length; idx++) {
                                    const h = idx < hlLen ? hl[idx] : ""
                                    const lbl = (typeof h === "object" && h !== null) ? (h.label || h.key || "") : String(h || "")
                                    const val = r[idx]
                                    out.push({ "label": lbl, "value": String(val === null || val === undefined ? "" : val) })
                                }
                                return out
                            }
                            if (r && typeof r === "object") {
                                if (hlLen > 0) {
                                    const out = []
                                    for (let i = 0; i < hlLen; i++) {
                                        const h = hl[i]
                                        const k = (typeof h === "object" && h !== null) ? (h.key || h.label || "") : String(h || "")
                                        const lbl = (typeof h === "object" && h !== null) ? (h.label || k) : String(h || "")
                                        const v = r[k]
                                        out.push({ "label": lbl, "value": String(v === null || v === undefined ? "" : v) })
                                    }
                                    return out
                                }
                                return Object.keys(r).map(function(k) {
                                    const v = r[k]
                                    return { "label": String(k), "value": String(v === null || v === undefined ? "" : v) }
                                })
                            }
                            return [{ "label": "", "value": String(r || "") }]
                        }

                        Layout.fillWidth: true
                        implicitHeight: rowFlow.implicitHeight + 16
                        radius: 8
                        color: desk.inputColor
                        border.width: 1
                        border.color: desk.edge

                        RowLayout {
                            id: rowFlow
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.top: parent.top
                            anchors.margins: 8
                            spacing: 12

                            Repeater {
                                model: tableRowCard.cellItems
                                delegate: ColumnLayout {
                                    required property var modelData
                                    Layout.fillWidth: true
                                    Layout.preferredWidth: 1
                                    Layout.alignment: Qt.AlignTop
                                    spacing: 2
                                    Label {
                                        visible: Boolean(modelData.label)
                                        text: modelData.label || ""
                                        font.pixelSize: 10
                                        font.weight: Font.Medium
                                        color: desk.muted
                                        wrapMode: Text.Wrap
                                        Layout.fillWidth: true
                                    }
                                    Label {
                                        text: modelData.value || ""
                                        font.pixelSize: 12
                                        font.weight: Font.Medium
                                        color: desk.ink
                                        wrapMode: Text.Wrap
                                        Layout.fillWidth: true
                                    }
                                }
                            }
                        }
                    }
                }
            }

            Label {
                visible: Boolean(cardRoot.cardData && cardRoot.cardData.summary)
                text: cardRoot.cardData ? (cardRoot.cardData.summary || "") : ""
                font.pixelSize: 12
                color: desk.muted
                wrapMode: Text.Wrap
                Layout.fillWidth: true
            }
        }

        // --- 6. TRẮC NGHIỆM ÔN TẬP (QUIZ) ---
        ColumnLayout {
            id: quizSection
            visible: cardRoot.visualType === "quiz"
            Layout.fillWidth: true
            spacing: 10
            property var selectedAnswers: ({})
            // Marked wrong in this view; questionData.flagged keeps it once the card is rebuilt.
            property var flaggedQuestions: ({})
            function isFlagged(i) {
                const qs = (cardRoot.cardData && cardRoot.cardData.questions) ? cardRoot.cardData.questions : []
                return Boolean(quizSection.flaggedQuestions[i] || (qs[i] && qs[i].flagged))
            }
            // A question the user marked wrong does not count toward the score.
            readonly property int answeredCount: {
                const ans = quizSection.selectedAnswers || ({})
                return Object.keys(ans).filter(k => !quizSection.isFlagged(Number(k))).length
            }
            readonly property int correctCount: {
                const qs = (cardRoot.cardData && cardRoot.cardData.questions) ? cardRoot.cardData.questions : []
                const ans = quizSection.selectedAnswers || ({})
                let hits = 0
                for (let i = 0; i < qs.length; i++) {
                    if (typeof ans[i] === "number" && qs[i] && ans[i] === qs[i].correct_index && !quizSection.isFlagged(i)) {
                        hits++
                    }
                }
                return hits
            }

            Connections {
                target: cardRoot
                function onCardDataChanged() {
                    quizSection.selectedAnswers = ({})
                    quizSection.flaggedQuestions = ({})
                }
            }

            RowLayout {
                spacing: 8
                Badge {
                    text: "📝 TRẮC NGHIỆM ÔN TẬP"
                    textColor: desk.accent
                    fontWeight: Font.DemiBold
                    color: Qt.rgba(desk.accent.r, desk.accent.g, desk.accent.b, 0.15)
                }
                Label {
                    text: cardRoot.cardData ? (cardRoot.cardData.title || "") : ""
                    font.pixelSize: 13
                    font.weight: Font.DemiBold
                    color: desk.ink
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                }
                Badge {
                    visible: quizSection.answeredCount > 0
                    text: "Đúng " + quizSection.correctCount + "/" + quizSection.answeredCount
                    textColor: desk.accent
                    fontWeight: Font.DemiBold
                }
                QuietButton {
                    objectName: "resetQuizButton"
                    // Any chosen answer, flagged or not: the score leaves flagged ones out, "Làm lại" does not.
                    visible: Object.keys(quizSection.selectedAnswers || ({})).length > 0
                    text: "Làm lại"
                    plain: true
                    font.pixelSize: 12
                    onClicked: quizSection.selectedAnswers = ({})
                }
            }

            Label {
                objectName: "quizInstruction"
                visible: text.length > 0
                text: cardRoot.cardData ? (cardRoot.cardData.instruction || "") : ""
                font.pixelSize: 12
                color: desk.muted
                wrapMode: Text.Wrap
                Layout.fillWidth: true
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 8

                Repeater {
                    model: cardRoot.cardData && cardRoot.cardData.questions ? cardRoot.cardData.questions : []
                    delegate: Rectangle {
                        id: quizQuestionCard
                        required property var modelData
                        required property int index
                        readonly property var questionData: modelData || ({})
                        readonly property int selectedIndex: (quizSection.selectedAnswers && typeof quizSection.selectedAnswers[quizQuestionCard.index] === "number")
                            ? quizSection.selectedAnswers[quizQuestionCard.index]
                            : -1
                        readonly property int correctIndex: typeof questionData.correct_index === "number" ? questionData.correct_index : -1
                        readonly property bool flagged: quizSection.flaggedQuestions[index] === true || questionData.flagged === true

                        Layout.fillWidth: true
                        implicitHeight: quizQuestionCol.implicitHeight + 18
                        opacity: flagged ? 0.6 : 1.0
                        radius: 8
                        color: desk.inputColor
                        border.width: 1
                        border.color: desk.edge

                        ColumnLayout {
                            id: quizQuestionCol
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.top: parent.top
                            anchors.margins: 9
                            spacing: 6

                            Label {
                                text: (quizQuestionCard.index + 1) + ". " + (quizQuestionCard.questionData.question || "")
                                font.pixelSize: 13
                                font.weight: Font.Medium
                                color: desk.ink
                                wrapMode: Text.Wrap
                                Layout.fillWidth: true
                            }

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 4

                                Repeater {
                                    model: quizQuestionCard.questionData.options || []
                                    delegate: Rectangle {
                                        id: optionBtn
                                        objectName: "quizOption_" + quizQuestionCard.index + "_" + optionBtn.index
                                        required property var modelData
                                        required property int index
                                        readonly property bool isChosen: quizQuestionCard.selectedIndex === index
                                        readonly property bool isAnswered: quizQuestionCard.selectedIndex >= 0
                                        readonly property bool isCorrect: quizQuestionCard.correctIndex === index

                                        Layout.fillWidth: true
                                        implicitHeight: optLabel.implicitHeight + 12
                                        radius: 6
                                        color: {
                                            if (isAnswered && isCorrect) return desk.selectedSurface
                                            if (isAnswered && isChosen && !isCorrect) return Qt.rgba(desk.warningInk.r, desk.warningInk.g, desk.warningInk.b, 0.14)
                                            return desk.utilitySurface
                                        }
                                        border.width: 1
                                        border.color: {
                                            if (isAnswered && isCorrect) return desk.accent
                                            if (isAnswered && isChosen && !isCorrect) return desk.warningInk
                                            return desk.edge
                                        }

                                        Label {
                                            id: optLabel
                                            anchors.fill: parent
                                            anchors.leftMargin: 10
                                            anchors.rightMargin: 10
                                            anchors.topMargin: 6
                                            anchors.bottomMargin: 6
                                            text: String(optionBtn.modelData || "")
                                            font.pixelSize: 12
                                            font.weight: (optionBtn.isAnswered && (optionBtn.isCorrect || optionBtn.isChosen)) ? Font.DemiBold : Font.Normal
                                            color: {
                                                if (optionBtn.isAnswered && optionBtn.isCorrect) return desk.accent
                                                if (optionBtn.isAnswered && optionBtn.isChosen && !optionBtn.isCorrect) return desk.warningInk
                                                return desk.ink
                                            }
                                            wrapMode: Text.Wrap
                                        }

                                        MouseArea {
                                            anchors.fill: parent
                                            cursorShape: Qt.PointingHandCursor
                                            onClicked: {
                                                var next = Object.assign({}, quizSection.selectedAnswers || ({}))
                                                next[quizQuestionCard.index] = optionBtn.index
                                                quizSection.selectedAnswers = next
                                            }
                                        }
                                    }
                                }
                            }

                            Label {
                                objectName: "quizQuoteLabel_" + quizQuestionCard.index
                                visible: quizQuestionCard.selectedIndex >= 0 && Boolean(quizQuestionCard.questionData.quote)
                                Layout.fillWidth: true
                                wrapMode: Text.Wrap
                                font.pixelSize: 11
                                color: (quizQuestionCard.selectedIndex === quizQuestionCard.correctIndex) ? desk.accent : desk.warningInk
                                text: {
                                    const verdict = (quizQuestionCard.selectedIndex === quizQuestionCard.correctIndex) ? "✓ Chính xác!" : "✗ Chưa đúng."
                                    const pg = quizQuestionCard.questionData.source_page
                                    const pgText = (pg && pg > 0) ? (" (Trang " + pg + ")") : ""
                                    return verdict + " Trích nguồn" + pgText + ": " + (quizQuestionCard.questionData.quote || "")
                                }
                            }

                            // Shown once answered: with the key and the quote in view, the user can tell a bad question.
                            QuietButton {
                                objectName: "quizFlag_" + quizQuestionCard.index
                                visible: quizQuestionCard.selectedIndex >= 0 && !quizQuestionCard.flagged
                                text: "Câu này sai"
                                plain: true
                                font.pixelSize: 11
                                Accessible.description: "Đánh dấu câu hỏi này sai; Chuột sẽ bỏ nó khỏi ghi chú"
                                onClicked: {
                                    if (desk.liveController && desk.liveController.flagQuizQuestion(quizQuestionCard.index)) {
                                        var next = Object.assign({}, quizSection.flaggedQuestions)
                                        next[quizQuestionCard.index] = true
                                        quizSection.flaggedQuestions = next
                                    }
                                }
                            }

                            Label {
                                objectName: "quizFlagged_" + quizQuestionCard.index
                                visible: quizQuestionCard.flagged
                                text: "Đã đánh dấu câu này sai. Chuột không tính nó vào điểm và sẽ bỏ nó khỏi ghi chú."
                                font.pixelSize: 11
                                color: desk.muted
                                wrapMode: Text.Wrap
                                Layout.fillWidth: true
                            }
                        }
                    }
                }
            }
        }
    }
}
