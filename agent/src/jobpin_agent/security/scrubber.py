"""Streaming fence scrubber — ported from Hermes (MIT).

EN —
Ported from Hermes ``agent/memory_manager.py::StreamingContextScrubber`` (MIT, Nous Research). The
one-shot ``sanitize_context`` regex (§1.3 ``memory/fence.py``) cannot survive chunk boundaries: a
``<memory-context>`` opened in one streamed delta and closed in a later delta would leak its payload to
the UI because the non-greedy block regex needs both tags in one string. This scrubber runs a small
state machine across deltas, holding back partial-tag tails and discarding everything inside a span
(including the system-note line). It is the streaming counterpart of the §1.3 fence; the real streaming
model path (token deltas) is wired at §1.11, where ``feed``/``flush`` wrap the model's output stream.

What changed vs Hermes (TEXTBOOK_SPEC Tenet 1): the state-machine logic is copied **verbatim**; only the
docstrings were made bilingual and this port-origin note added. The block-boundary logic matches Jobpin's
§1.3 fence rendering (open tag starts a line and is followed by a newline).

中文 —
移植自 Hermes ``agent/memory_manager.py::StreamingContextScrubber``（MIT，Nous Research）。一次性的
``sanitize_context`` 正则（§1.3 ``memory/fence.py``）无法跨块边界存活：在一个流式 delta 中开启、在后续 delta 中关闭的
``<memory-context>`` 会把其载荷泄漏给 UI，因为非贪婪块正则需要两个标签在同一字符串中。本清洗器跨 delta 运行一个小状态机，
保留部分标签尾部并丢弃 span 内全部内容（含系统提示行）。它是 §1.3 围栏的流式对应物；真实流式模型路径（token deltas）在
§1.11 接线，届时 ``feed``/``flush`` 包裹模型输出流。

相对 Hermes 的改动（TEXTBOOK_SPEC 第一原则）：状态机逻辑逐字复制；仅将文档串双语化并加此移植说明。块边界逻辑与 Jobpin
§1.3 围栏渲染一致（开标签起于行首且其后接换行）。
"""
from __future__ import annotations


class StreamingContextScrubber:
    """Stateful scrubber for streaming text that may contain split memory-context spans (ported).

    EN —
    Usage: create one per top-level response (new turn); ``feed(delta)`` each chunk and emit the returned
    visible portion; call ``flush()`` at end-of-stream. An open span never closed is discarded on flush
    (leaking partial memory is worse than a truncated reply). Call ``reset()`` to reuse the instance.

    中文 —
    用法：每个顶层响应（新回合）创建一个；对每块调用 ``feed(delta)`` 并发出返回的可见部分；流末调用 ``flush()``。
    未关闭的开启 span 在 flush 时被丢弃（泄漏部分记忆比截断答复更糟）。调用 ``reset()`` 复用实例。
    """

    _OPEN_TAG = "<memory-context>"
    _CLOSE_TAG = "</memory-context>"

    def __init__(self) -> None:
        """Initialise the scrubber state (not in a span, empty buffer, at a block boundary).

        EN: Returns: None. 中文：返回：None。
        """
        self._in_span: bool = False
        self._buf: str = ""
        self._at_block_boundary: bool = True

    def reset(self) -> None:
        """Reset to the initial state for reuse on a new top-level response.

        EN: Returns: None. 中文：返回：None。
        """
        self._in_span = False
        self._buf = ""
        self._at_block_boundary = True

    def feed(self, text: str) -> str:
        """Return the visible portion of ``text`` after scrubbing fenced spans.

        EN: Args: text (a streamed delta). Returns: the safe-to-emit portion; a trailing fragment that
            could begin an open/close tag is held back for the next ``feed`` or ``flush``.
        中文：参数：text（流式 delta）。返回：可安全发出的部分；可能开启开/闭标签的尾片被保留，待下次 ``feed`` 或 ``flush``。
        """
        if not text:
            return ""
        buf = self._buf + text
        self._buf = ""
        out: list[str] = []

        while buf:
            if self._in_span:
                idx = buf.lower().find(self._CLOSE_TAG)
                if idx == -1:
                    held = self._max_partial_suffix(buf, self._CLOSE_TAG)
                    self._buf = buf[-held:] if held else ""
                    return "".join(out)
                buf = buf[idx + len(self._CLOSE_TAG):]
                self._in_span = False
            else:
                idx = self._find_boundary_open_tag(buf)
                if idx == -1:
                    held = (
                        self._max_pending_open_suffix(buf)
                        or self._max_partial_suffix(buf, self._OPEN_TAG)
                    )
                    if held:
                        self._append_visible(out, buf[:-held])
                        self._buf = buf[-held:]
                    else:
                        self._append_visible(out, buf)
                    return "".join(out)
                if idx > 0:
                    self._append_visible(out, buf[:idx])
                buf = buf[idx + len(self._OPEN_TAG):]
                self._in_span = True

        return "".join(out)

    def flush(self) -> str:
        """Emit any held-back buffer at end-of-stream (discard an unterminated span).

        EN: Returns: the held-back non-tag tail, or "" if still inside an unclosed span (discarded).
        中文：返回：保留的非标签尾部，或若仍在未关闭 span 内则 ""（丢弃）。
        """
        if self._in_span:
            self._buf = ""
            self._in_span = False
            return ""
        tail = self._buf
        self._buf = ""
        return tail

    @staticmethod
    def _max_partial_suffix(buf: str, tag: str) -> int:
        """Return the length of the longest buf-suffix that is a prefix of ``tag`` (case-insensitive).

        EN: Args: buf; tag. Returns: the suffix length (0 if none could start the tag).
        中文：参数：buf；tag。返回：后缀长度（无可起始则 0）。
        """
        tag_lower = tag.lower()
        buf_lower = buf.lower()
        max_check = min(len(buf_lower), len(tag_lower) - 1)
        for i in range(max_check, 0, -1):
            if tag_lower.startswith(buf_lower[-i:]):
                return i
        return 0

    def _find_boundary_open_tag(self, buf: str) -> int:
        """Find an opening fence only when it starts a block-like span.

        EN: Args: buf. Returns: the index of a block-boundary open tag, or -1.
        中文：参数：buf。返回：块边界开标签的索引，或 -1。
        """
        buf_lower = buf.lower()
        search_start = 0
        while True:
            idx = buf_lower.find(self._OPEN_TAG, search_start)
            if idx == -1:
                return -1
            if self._is_block_boundary(buf, idx) and self._has_block_opener_suffix(buf, idx):
                return idx
            search_start = idx + 1

    def _max_pending_open_suffix(self, buf: str) -> int:
        """Hold a complete boundary open tag until the following char confirms it.

        EN: Args: buf. Returns: ``len(open_tag)`` if buf ends with a boundary open tag, else 0.
        中文：参数：buf。返回：若 buf 以块边界开标签结尾则 ``len(open_tag)``，否则 0。
        """
        if not buf.lower().endswith(self._OPEN_TAG):
            return 0
        idx = len(buf) - len(self._OPEN_TAG)
        if not self._is_block_boundary(buf, idx):
            return 0
        return len(self._OPEN_TAG)

    def _has_block_opener_suffix(self, buf: str, idx: int) -> bool:
        """Whether the char after the open tag at ``idx`` is a newline (block opener).

        EN: Args: buf; idx. Returns: True if the next char is CR/LF. 中文：参数：buf；idx。返回：下一字符为 CR/LF 则 True。
        """
        after_idx = idx + len(self._OPEN_TAG)
        if after_idx >= len(buf):
            return False
        return buf[after_idx] in "\r\n"

    def _is_block_boundary(self, buf: str, idx: int) -> bool:
        """Whether position ``idx`` begins a line (only blanks since the last newline).

        EN: Args: buf; idx. Returns: True at a block boundary. 中文：参数：buf；idx。返回：处于块边界则 True。
        """
        if idx == 0:
            return self._at_block_boundary
        preceding = buf[:idx]
        last_newline = preceding.rfind("\n")
        if last_newline == -1:
            return self._at_block_boundary and preceding.strip() == ""
        return preceding[last_newline + 1:].strip() == ""

    def _append_visible(self, out: list[str], text: str) -> None:
        """Append visible text to the output and update the block-boundary flag.

        EN: Args: out; text. Returns: None. 中文：参数：out；text。返回：None。
        """
        if not text:
            return
        out.append(text)
        self._update_block_boundary(text)

    def _update_block_boundary(self, text: str) -> None:
        """Track whether the emitted text ends at a fresh-line boundary.

        EN: Args: text. Returns: None. 中文：参数：text。返回：None。
        """
        last_newline = text.rfind("\n")
        if last_newline != -1:
            self._at_block_boundary = text[last_newline + 1:].strip() == ""
        else:
            self._at_block_boundary = self._at_block_boundary and text.strip() == ""


__all__ = ["StreamingContextScrubber"]
