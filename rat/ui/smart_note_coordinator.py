"""
rat.ui.smart_note_coordinator — Standalone coordinator for Smart Notes lifecycle and execution.

Manages synthesis, checklist action-item toggles, and section expansion through
the unified AgentExecutionService, independent of any domain vertical plugin.
"""
from __future__ import annotations

from typing import Any, Dict, Optional
from uuid import uuid4

from rat.engine.execution import ExecutionRequest
from rat.engine.execution_service import AgentExecutionService


class SmartNoteCoordinator:
    """Manages active Smart Note state and dispatches Smart Note actions via AgentExecutionService."""

    def __init__(self, controller) -> None:
        self.controller = controller
        self.active_note: Optional[Dict[str, Any]] = None
        self.active_note_id: Optional[str] = None
        self.active_note_revision: int = 0
        self.result_refs: Dict[str, Dict[str, Any]] = {}
        self.error: str = ""

    def synthesize_smart_note(
        self,
        raw_content: str,
        domain: str = "auto",
        title: str = "",
        focus_question: str = "",
        *,
        extra_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        ctrl = self.controller
        if ctrl._closed:
            return ""
        text = (raw_content or "").strip()
        if not text:
            self.error = "Cần cung cấp nội dung để tạo ghi chú."
            ctrl.changed.emit()
            return ""
        args: Dict[str, Any] = {
            "raw_content": text,
            "domain": domain or "auto",
        }
        if title:
            args["title"] = title
        if focus_question:
            args["focus_question"] = focus_question

        ctx: Dict[str, Any] = {}
        if extra_context:
            ctx.update(extra_context)

        exec_id = "smart-note-" + uuid4().hex
        req = ExecutionRequest(
            f"Tổng hợp ghi chú: {title or 'thông minh'}",
            execution_id=exec_id,
            origin="ui_action",
            requested_action={"name": "synthesize_smart_note", "args": args},
            context=ctx,
        )
        service = AgentExecutionService(ctrl.assistant_runtime)
        resp = service.execute(req)
        if resp.error or not resp.artifacts:
            self.error = resp.error or "Không thể tổng hợp ghi chú thông minh."
            ctrl.changed.emit()
            return ""

        artifact = resp.artifacts[0]
        self.active_note = artifact.payload
        self.active_note_id = artifact.id
        self.active_note_revision = artifact.revision
        self.result_refs["synthesize_smart_note"] = {
            "artifact_id": artifact.id,
            "revision": artifact.revision,
        }
        self.error = ""
        ctrl._status = f"Đã lưu ghi chú: {artifact.payload.get('title', '')}"
        ctrl._events.append(f"Ghi chú thông minh đã tạo (rev {artifact.revision}): {artifact.id}")
        ctrl.changed.emit()
        return artifact.id

    def update_note_action_item(
        self,
        task_match: str = "",
        done: bool = True,
        item_index: Optional[int] = None,
        artifact_id: Optional[str] = None,
        new_task_text: Optional[str] = None,
    ) -> bool:
        ctrl = self.controller
        if ctrl._closed:
            return False
        target_id = artifact_id or self.active_note_id
        target_rev = (
            self.active_note_revision
            if (not artifact_id or artifact_id == self.active_note_id)
            else None
        )
        if not target_id:
            self.error = "Chưa có bản ghi chú nào được chọn để cập nhật việc cần làm."
            ctrl.changed.emit()
            return False

        args: Dict[str, Any] = {
            "artifact_id": target_id,
            "done": done,
        }
        if target_rev is not None:
            args["revision"] = target_rev
        if task_match:
            args["task_match"] = task_match
        if item_index is not None:
            args["item_index"] = item_index
        if new_task_text:
            args["new_task_text"] = new_task_text

        exec_id = "update-note-" + uuid4().hex
        req = ExecutionRequest(
            f"Cập nhật việc cần làm trong ghi chú {target_id}",
            execution_id=exec_id,
            origin="ui_action",
            requested_action={"name": "update_note_action_item", "args": args},
            context={},
        )
        service = AgentExecutionService(ctrl.assistant_runtime)
        resp = service.execute(req)
        if resp.error or not resp.artifacts:
            self.error = resp.error or "Không cập nhật được việc cần làm."
            ctrl.changed.emit()
            return False

        artifact = resp.artifacts[0]
        self.active_note = artifact.payload
        self.active_note_id = artifact.id
        self.active_note_revision = artifact.revision
        self.result_refs["update_note_action_item"] = {
            "artifact_id": artifact.id,
            "revision": artifact.revision,
        }
        self.error = ""
        action_name = task_match or (f"mục #{item_index}" if item_index is not None else "việc cần làm")
        state_label = "hoàn thành" if done else "chưa xong"
        ctrl._status = f"Đã cập nhật việc cần làm: {action_name} -> {state_label}"
        ctrl._events.append(f"Cập nhật việc cần làm ghi chú: rev {artifact.revision}")
        ctrl.changed.emit()
        return True

    def expand_note_section(
        self,
        section_heading: str,
        expansion_content: str = "",
        expansion_query: str = "",
        artifact_id: Optional[str] = None,
    ) -> bool:
        ctrl = self.controller
        if ctrl._closed:
            return False
        target_id = artifact_id or self.active_note_id
        target_rev = (
            self.active_note_revision
            if (not artifact_id or artifact_id == self.active_note_id)
            else None
        )
        if not target_id:
            self.error = "Chưa có bản ghi chú nào được chọn để mở rộng mục."
            ctrl.changed.emit()
            return False

        heading = (section_heading or "").strip()
        if not heading:
            self.error = "Cần chỉ định tên mục cần mở rộng (section_heading)."
            ctrl.changed.emit()
            return False

        content = (expansion_content or "").strip()
        query = (expansion_query or "").strip() or f"Đào sâu mục {heading}"
        if not content:
            content = (
                f"Phân tích bổ sung về {query}: "
                "Các khía cạnh thực tế và đề xuất thực hiện chi tiết."
            )

        args: Dict[str, Any] = {
            "artifact_id": target_id,
            "section_heading": heading,
            "expansion_content": content,
            "expansion_query": query,
        }
        if target_rev is not None:
            args["revision"] = target_rev

        exec_id = "expand-note-" + uuid4().hex
        req = ExecutionRequest(
            f"Mở rộng mục {heading} trong ghi chú {target_id}",
            execution_id=exec_id,
            origin="ui_action",
            requested_action={"name": "expand_note_section", "args": args},
            context={},
        )
        service = AgentExecutionService(ctrl.assistant_runtime)
        resp = service.execute(req)
        if resp.error or not resp.artifacts:
            self.error = resp.error or "Không mở rộng được mục ghi chú."
            ctrl.changed.emit()
            return False

        artifact = resp.artifacts[0]
        self.active_note = artifact.payload
        self.active_note_id = artifact.id
        self.active_note_revision = artifact.revision
        self.result_refs["expand_note_section"] = {
            "artifact_id": artifact.id,
            "revision": artifact.revision,
        }
        self.error = ""
        ctrl._status = f"Đã mở rộng mục: {heading}"
        ctrl._events.append(f"Mở rộng mục ghi chú: rev {artifact.revision}")
        ctrl.changed.emit()
        return True
