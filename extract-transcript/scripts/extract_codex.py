"""Map Codex transcript records to normalized content records."""

import json
import re
from pathlib import Path

from extract_shared import (
    earliest_timestamp,
    normalized_agent_instructions_record,
    normalized_content_record,
    normalized_reasoning_record,
    normalized_tool_call_record,
    normalized_tool_result_record,
    normalized_turn_lifecycle_record,
    session_basic_data,
    split_tool_result_content,
    tool_lifecycle_report,
    tool_result_report,
    tool_lifecycle_status,
    unmatched_tool_result_report,
)


_EVENT_CONTENT_CATEGORIES = {
    "user_message": "user_prompt",
    "agent_message": "user_visible_agent_output",
}
_ITEM_MESSAGE_CATEGORIES = {
    "UserMessage": "user_prompt",
    "AgentMessage": "user_visible_agent_output",
}
# Sub-agent collaboration tools whose response_item call/output activity this
# adapter extracts; SubAgentActivity and CollabAgentToolCall items only echo
# that activity, so each item is noise solely when the tool stream exists.
_COLLAB_AGENT_TOOL_NAMES = frozenset({
    "list_agents",
    "send_message",
    "spawn_agent",
    "wait_agent",
})
_FILES_MENTIONED_PREFIX = "# Files mentioned by the user:"
_USER_REQUEST_MARKER = "## My request for Codex:"
_PAIRED_CALL_TYPES = frozenset({
    "custom_tool_call",
    "function_call",
    "tool_search_call",
})
_PAIRED_RESULT_TYPES = frozenset({
    "custom_tool_call_output",
    "function_call_output",
    "tool_search_output",
})
_SELF_CONTAINED_RESPONSE_TYPES = frozenset({
    "image_generation_call",
    "web_search_call",
})
_SELF_CONTAINED_EVENT_TYPES = frozenset({
    "mcp_tool_call_end",
    "view_image_tool_call",
})
INTERACTIVE_QUESTION_TOOLS = frozenset({"request_user_input"})
_PROGRESS_EVENT_TYPES = frozenset({
    "agent_message",
    "item_completed",
    "task_complete",
    "turn_aborted",
    "user_message",
})
_TURN_LIFECYCLE_EVENTS = {
    "task_started": (
        "started",
        (
            "turn_id",
            "started_at",
            "collaboration_mode_kind",
            "model_context_window",
        ),
    ),
    "task_complete": (
        "completed",
        (
            "turn_id",
            "started_at",
            "completed_at",
            "duration_ms",
            "time_to_first_token_ms",
        ),
    ),
    "turn_aborted": (
        "interrupted",
        ("turn_id", "started_at", "completed_at", "duration_ms", "reason"),
    ),
}
_SKILLS_WRAPPER_RE = re.compile(
    r"\A\s*<skills_instructions>(.*)</skills_instructions>\s*\Z",
    re.DOTALL,
)
_SKILLS_INDEX_HEADINGS = frozenset({
    "## Skills",
    "### Skill roots",
    "### Available skills",
})
_SKILLS_INDEX_PREAMBLE_PREFIXES = (
    "A skill is a set of local instructions",
    "Below is the list of skills",
    "Installed skill index.",
)
_SKILL_ROOT_ENTRY_RE = re.compile(r"- `?r\d+`?\s*=.*")
_AVAILABLE_SKILL_ENTRY_RE = re.compile(r"- .+?: .+\(file: .+\)")
_EXTRACT_TRANSCRIPT_SKILL_RE = re.compile(
    r"<skill>\s*<name>extract-transcript</name>",
    re.DOTALL,
)
_PROJECT_INSTRUCTIONS_RE = re.compile(
    r"\A# AGENTS\.md instructions(?: for [^\n]+)?\n+"
    r"<INSTRUCTIONS>.*</INSTRUCTIONS>\s*\Z",
    re.DOTALL,
)
_RUNTIME_USER_INSTRUCTION_RES = (
    ("skill", re.compile(r"\A\s*<skill>.*</skill>\s*\Z", re.DOTALL)),
    ("hook", re.compile(r"\A\s*<hook_prompt>.*</hook_prompt>\s*\Z", re.DOTALL)),
    (
        "permission",
        re.compile(
            r"\A\s*<permissions instructions>.*</permissions instructions>\s*\Z",
            re.DOTALL,
        ),
    ),
)
_RUNTIME_USER_CONTEXT_NOISE_RES = (
    re.compile(
        r"\A\s*<recommended_plugins>.*</recommended_plugins>\s*\Z",
        re.DOTALL,
    ),
    re.compile(
        r"\A\s*<environment_context>.*</environment_context>\s*\Z",
        re.DOTALL,
    ),
)
_VIEW_IMAGE_DATA_URL_RE = re.compile(
    r"\Adata:(image/(?:gif|jpeg|png|webp));base64,(.+)\Z",
    re.DOTALL,
)
_HIDDEN_MEMORY_CITATION_SUFFIX_RE = re.compile(
    r"(?:\n\n)?<oai-mem-citation>.*?</oai-mem-citation>\s*\Z",
    re.DOTALL,
)
_SESSION_DATA_EVENT_TYPES = frozenset({
    "thread_settings_applied",
    "token_count",
})
# agent_reasoning events mirror the response_item reasoning summaries this
# adapter extracts; context_compacted events only mark history compaction.
_NOISE_EVENT_TYPES = frozenset({"agent_reasoning", "context_compacted"})
# ContextCompaction items are the item_completed form of context_compacted:
# both only mark history compaction and carry no content of their own.
_NOISE_ITEM_TYPES = frozenset({"ContextCompaction"})
# Codex records native extension activity as one self-contained Extension
# item. web.search keeps the name the web_search_call response_item produced,
# so the normalized tool name survives the source-shape change.
_EXTENSION_TOOL_NAMES = {"web.search": "web_search"}
# These end events only mirror a response_item call the adapter extracts, so
# each one is noise solely when that paired call exists in the same source.
_MIRROR_END_EVENT_TYPES = frozenset({"exec_command_end", "patch_apply_end"})
_RECOGNIZED_EVENT_TYPES = (
    frozenset(_EVENT_CONTENT_CATEGORIES)
    | frozenset(_TURN_LIFECYCLE_EVENTS)
    | _SELF_CONTAINED_EVENT_TYPES
    | _SESSION_DATA_EVENT_TYPES
    | _NOISE_EVENT_TYPES
)
_RECOGNIZED_RESPONSE_TYPES = (
    frozenset({"reasoning"})
    | _PAIRED_CALL_TYPES
    | _PAIRED_RESULT_TYPES
    | _SELF_CONTAINED_RESPONSE_TYPES
)
_MESSAGE_ROLES = frozenset({"assistant", "developer", "system", "user"})


def _completed_item(record):
    """Return one item_completed event's inner item when it is inspectable."""
    payload = record.get("payload")
    if not (
        record.get("type") == "event_msg"
        and isinstance(payload, dict)
        and payload.get("type") == "item_completed"
    ):
        return None
    item = payload.get("item")
    return item if isinstance(item, dict) else None


def _content_blocks_text(container):
    """Join the readable text blocks of an item or message payload."""
    content = container.get("content")
    if not isinstance(content, list):
        return ""
    return "\n".join(
        block["text"]
        for block in content
        if (
            isinstance(block, dict)
            and isinstance(block.get("text"), str)
            and block["text"]
        )
    )


def _mirror_context(records):
    """Summarize which mirrored response_item streams this source records."""
    context = {
        "paired_call_ids": set(),
        "paired_message_record_indexes": set(),
        "has_exec_tool_calls": False,
        "exec_tool_call_turn_ids": set(),
        "has_collab_tool_calls": False,
        "reasoning_ids": set(),
    }
    for record in records:
        payload = record.get("payload")
        if not (
            record.get("type") == "response_item"
            and isinstance(payload, dict)
        ):
            continue
        payload_type = payload.get("type")
        if payload_type in _PAIRED_CALL_TYPES and payload.get("call_id"):
            context["paired_call_ids"].add(payload["call_id"])
        if payload_type == "custom_tool_call":
            context["has_exec_tool_calls"] = True
            metadata = payload.get("internal_chat_message_metadata_passthrough")
            turn_id = metadata.get("turn_id") if isinstance(metadata, dict) else None
            if turn_id:
                context["exec_tool_call_turn_ids"].add(turn_id)
        elif (
            payload_type == "function_call"
            and payload.get("name") in _COLLAB_AGENT_TOOL_NAMES
        ):
            context["has_collab_tool_calls"] = True
        elif payload_type == "reasoning" and payload.get("id"):
            context["reasoning_ids"].add(payload["id"])

    available_message_mirrors = {}
    for record in records:
        mirror_key = _message_mirror_key(record)
        if mirror_key is not None:
            available_message_mirrors[mirror_key] = (
                available_message_mirrors.get(mirror_key, 0) + 1
            )
    for record_index, record in enumerate(records):
        payload = record.get("payload")
        if not (
            record.get("type") == "response_item"
            and isinstance(payload, dict)
            and payload.get("type") == "message"
            and payload.get("role") in ("assistant", "user")
        ):
            continue
        mirror_key = (payload["role"], _message_mirror_text(payload))
        if not available_message_mirrors.get(mirror_key):
            continue
        context["paired_message_record_indexes"].add(record_index)
        available_message_mirrors[mirror_key] -= 1
    return context


def _message_mirror_key(record):
    """Return the role and text a message event positively mirrors."""
    payload = record.get("payload")
    if not (record.get("type") == "event_msg" and isinstance(payload, dict)):
        return None
    payload_type = payload.get("type")
    if payload_type in _EVENT_CONTENT_CATEGORIES:
        text = payload.get("message")
        return (
            ("user" if payload_type == "user_message" else "assistant", text)
            if isinstance(text, str)
            else None
        )
    item = _completed_item(record)
    if item is None or item.get("type") not in _ITEM_MESSAGE_CATEGORIES:
        return None
    return (
        "user" if item["type"] == "UserMessage" else "assistant",
        _content_blocks_text(item),
    )


def _message_mirror_text(payload):
    """Remove known hidden transport suffixes before mirror matching."""
    return _HIDDEN_MEMORY_CITATION_SUFFIX_RE.sub("", _message_text(payload))


def _is_standalone_command_execution(payload, mirrors):
    """Decide whether a CommandExecution item is itself the tool activity.

    The exec tool-call stream and CommandExecution items never share ids, so
    a command item defaults to being that stream's display copy whenever the
    stream exists; only turn evidence on both sides can positively separate
    an independently run command from the stream's commands.
    """
    if not mirrors["has_exec_tool_calls"]:
        return True
    turn_id = payload.get("turn_id")
    return bool(
        turn_id
        and mirrors["exec_tool_call_turn_ids"]
        and turn_id not in mirrors["exec_tool_call_turn_ids"]
    )


def unrecognized_records(records):
    """Return the source records no positive Codex classification covers."""
    mirrors = _mirror_context(records)
    return [
        record
        for record_index, record in enumerate(records)
        if not _is_recognized(record, mirrors, record_index)
    ]


def _is_recognized_item(item, mirrors):
    item_type = item.get("type")
    if item_type in _ITEM_MESSAGE_CATEGORIES:
        return isinstance(item.get("content"), list)
    if item_type in ("CommandExecution", "Extension", "Reasoning"):
        return True
    if item_type == "FileChange":
        return isinstance(item.get("changes"), dict)
    if item_type == "McpToolCall":
        return (
            isinstance(item.get("server"), str)
            and isinstance(item.get("tool"), str)
            and "arguments" in item
        )
    if item_type in _NOISE_ITEM_TYPES:
        return True
    if item_type in ("CollabAgentToolCall", "SubAgentActivity"):
        return mirrors["has_collab_tool_calls"]
    return False


def _is_recognized(record, mirrors, record_index):
    record_type = record.get("type")
    payload = record.get("payload")
    if not isinstance(payload, dict):
        return False
    if record_type == "token_usage_record":
        return isinstance(payload.get("thread_token_usage"), dict)
    if record_type == "compacted":
        # Compaction markers carry their replacement summary as "message".
        return "message" in payload
    if record_type in ("inter_agent_communication_metadata", "session_meta",
                       "turn_context"):
        return True
    if record_type == "world_state":
        return isinstance(payload.get("state"), dict)
    payload_type = payload.get("type")
    if record_type == "event_msg":
        if payload_type == "item_completed":
            item = payload.get("item")
            return isinstance(item, dict) and _is_recognized_item(item, mirrors)
        if payload_type in _MIRROR_END_EVENT_TYPES:
            return payload.get("call_id") in mirrors["paired_call_ids"]
        return payload_type in _RECOGNIZED_EVENT_TYPES
    if record_type == "response_item":
        if payload_type == "message":
            role = payload.get("role")
            if role not in _MESSAGE_ROLES:
                return False
            if role in ("developer", "system"):
                return True
            if record_index in mirrors["paired_message_record_indexes"]:
                return True
            return (
                role == "user"
                and _is_runtime_user_context_message(payload)
            )
        if payload_type == "agent_message":
            return isinstance(payload.get("content"), list)
        return payload_type in _RECOGNIZED_RESPONSE_TYPES
    return False


def _session_meta(records):
    return next(
        (
            record.get("payload")
            for record in records
            if (
                record.get("type") == "session_meta"
                and isinstance(record.get("payload"), dict)
            )
        ),
        None,
    )


def _spawn_launches(records):
    returned_task_names = {}
    for record in records:
        payload = record.get("payload")
        if not (
            record.get("type") == "response_item"
            and isinstance(payload, dict)
            and payload.get("type") == "function_call_output"
            and isinstance(payload.get("call_id"), str)
        ):
            continue
        output = payload.get("output")
        if isinstance(output, str):
            try:
                output = json.loads(output)
            except json.JSONDecodeError:
                output = None
        if isinstance(output, dict) and isinstance(output.get("task_name"), str):
            returned_task_names[payload["call_id"]] = output["task_name"]

    launches = []
    for record in records:
        payload = record.get("payload")
        if not (
            record.get("type") == "response_item"
            and isinstance(payload, dict)
            and payload.get("type") == "function_call"
            and payload.get("name") == "spawn_agent"
        ):
            continue
        call_id = payload.get("call_id")
        arguments = payload.get("arguments")
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments)
            except json.JSONDecodeError:
                arguments = None
        requested_task_name = (
            arguments.get("task_name") if isinstance(arguments, dict) else None
        )
        returned_task_name = returned_task_names.get(call_id)
        launches.append({
            "agent_path": returned_task_name,
            "label": returned_task_name or requested_task_name or call_id
            or "unidentified spawn_agent launch",
        })
    return launches


def discover_launched_agent_transcripts(source_path, records):
    """Return Codex children whose session metadata names this parent thread."""
    launches = _spawn_launches(records)
    if not launches:
        return [], []

    session_meta = _session_meta(records)
    parent_thread_id = session_meta.get("id") if session_meta else None
    if not isinstance(parent_thread_id, str) or not parent_thread_id:
        return [], [
            "Codex launched-agent discovery is unavailable: parent thread id "
            "is missing"
        ]

    children = []
    source_path = Path(source_path).resolve()
    for candidate in sorted(source_path.parent.glob("*.jsonl")):
        if candidate.resolve() == source_path:
            continue
        try:
            with candidate.open(encoding="utf-8") as transcript:
                candidate_meta = None
                for raw_line in transcript:
                    try:
                        record = json.loads(raw_line)
                    except json.JSONDecodeError:
                        continue
                    if (
                        isinstance(record, dict)
                        and record.get("type") == "session_meta"
                    ):
                        candidate_meta = record.get("payload")
                        break
        except (OSError, UnicodeError):
            continue
        if not isinstance(candidate_meta, dict):
            continue
        source = candidate_meta.get("source")
        subagent = source.get("subagent") if isinstance(source, dict) else None
        thread_spawn = (
            subagent.get("thread_spawn") if isinstance(subagent, dict) else None
        )
        if (
            isinstance(thread_spawn, dict)
            and thread_spawn.get("parent_thread_id") == parent_thread_id
        ):
            children.append((candidate, thread_spawn.get("agent_path")))

    unmatched_launches = list(launches)
    child_paths = []
    conditions = []
    for child_path, agent_path in children:
        child_paths.append(child_path)
        matching_index = next(
            (
                index
                for index, launch in enumerate(unmatched_launches)
                if (
                    isinstance(agent_path, str)
                    and launch["agent_path"] == agent_path
                )
            ),
            None,
        )
        if matching_index is None:
            conditions.append(
                "Codex child {} could not be matched to a retained "
                "spawn_agent result".format(agent_path or child_path.name)
            )
        else:
            unmatched_launches.pop(matching_index)
    for launch in unmatched_launches:
        conditions.append(
            "Codex launched agent {} has no discoverable transcript".format(
                launch["label"]
            )
        )
    return child_paths, conditions


def _instruction_text(value):
    if isinstance(value, str):
        return value if value.strip() else None
    if isinstance(value, dict):
        text = value.get("text")
        return text if isinstance(text, str) and text.strip() else None
    return None


def _message_text(payload):
    if not isinstance(payload, dict) or payload.get("type") != "message":
        return ""
    content = payload.get("content")
    if not isinstance(content, list):
        return ""
    return "\n".join(
        text
        for block in content
        for text in (_instruction_text(block),)
        if text is not None
    )


def _reasoning_summary_text(payload):
    summary = payload.get("summary")
    if not isinstance(summary, list):
        return ""
    return "\n".join(
        block["text"]
        for block in summary
        if (
            isinstance(block, dict)
            and block.get("type") == "summary_text"
            and isinstance(block.get("text"), str)
            and block["text"]
        )
    )


def _reasoning_item_summary_text(item):
    summary = item.get("summary_text")
    if not isinstance(summary, list):
        return ""
    parts = []
    for block in summary:
        if isinstance(block, str) and block:
            parts.append(block)
        elif (
            isinstance(block, dict)
            and isinstance(block.get("text"), str)
            and block["text"]
        ):
            parts.append(block["text"])
    return "\n".join(parts)


def _reasoning_shapes(records):
    """Yield each reasoning shape with its entity key and readable text."""
    for index, record in enumerate(records):
        payload = record.get("payload")
        if (
            record.get("type") == "response_item"
            and isinstance(payload, dict)
            and payload.get("type") == "reasoning"
        ):
            key = ("id", payload["id"]) if payload.get("id") else ("record", index)
            yield key, _reasoning_summary_text(payload)
            continue
        item = _completed_item(record)
        if item is not None and item.get("type") == "Reasoning":
            key = ("id", item["id"]) if item.get("id") else ("record", index)
            yield key, _reasoning_item_summary_text(item)


def _encrypted_only_reasoning_count(records):
    """Count reasoning entities whose every recorded shape is unreadable."""
    entity_keys = set()
    readable_keys = set()
    for key, readable_text in _reasoning_shapes(records):
        entity_keys.add(key)
        if readable_text:
            readable_keys.add(key)
    return len(entity_keys - readable_keys)


def omitted_content_reports(records):
    """Report the per-category source content this adapter cannot deliver."""
    encrypted_only = _encrypted_only_reasoning_count(records)
    if not encrypted_only:
        return {}
    return {
        "reasoning": [
            "encrypted-only reasoning records were omitted "
            "(count: {})".format(encrypted_only)
        ],
    }


def current_session_cutoff(records):
    """Return the first source record for this attached skill invocation."""
    skill_index = None
    for index in range(len(records) - 1, -1, -1):
        record = records[index]
        payload = record.get("payload")
        if (
            record.get("type") == "response_item"
            and isinstance(payload, dict)
            and payload.get("role") == "user"
            and _EXTRACT_TRANSCRIPT_SKILL_RE.search(_message_text(payload))
        ):
            skill_index = index
            break
    if skill_index is None:
        return None

    for event_index in range(skill_index - 1, -1, -1):
        submitted_text = _submitted_event_text(records[event_index])
        if submitted_text is None:
            continue
        cutoff = event_index
        if event_index > 0:
            previous = records[event_index - 1]
            previous_payload = previous.get("payload")
            if (
                previous.get("type") == "response_item"
                and isinstance(previous_payload, dict)
                and previous_payload.get("role") == "user"
                and _message_text(previous_payload) == submitted_text
            ):
                cutoff -= 1
        return cutoff
    return None


def _submitted_event_text(record):
    """Return the text an event proves the user submitted, if it is one."""
    payload = record.get("payload")
    if not (record.get("type") == "event_msg" and isinstance(payload, dict)):
        return None
    if payload.get("type") == "user_message":
        message = payload.get("message")
        return message if isinstance(message, str) else None
    item = _completed_item(record)
    if item is not None and item.get("type") == "UserMessage":
        text = _content_blocks_text(item)
        return text or None
    return None


def active_session_evidence(records):
    """Return whether a source record directly says work is still running."""
    active_statuses = frozenset({"generating", "in_progress", "running"})
    for index, record in enumerate(records):
        payload = record.get("payload")
        if not (
            isinstance(payload, dict)
            and payload.get("status") in active_statuses
        ):
            continue
        call_id = payload.get("call_id")
        has_matching_result = any(
            (
                call_id
                and isinstance(later_payload, dict)
                and later_payload.get("call_id") == call_id
                and later_payload.get("type") in _PAIRED_RESULT_TYPES
            )
            for later_record in records[index + 1:]
            for later_payload in (later_record.get("payload"),)
        )
        if not (
            has_matching_result
            or _has_progress_evidence_after(records, index)
        ):
            return True
    return False


def _skills_index_residue(text):
    """Keep only the instruction lines a skills index carries beside entries."""
    substantive_lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if (
            not stripped
            or stripped in _SKILLS_INDEX_HEADINGS
            or stripped.startswith(_SKILLS_INDEX_PREAMBLE_PREFIXES)
            or _SKILL_ROOT_ENTRY_RE.fullmatch(stripped)
            or _AVAILABLE_SKILL_ENTRY_RE.fullmatch(stripped)
        ):
            continue
        substantive_lines.append(line)
    substantive_text = "\n".join(substantive_lines).strip()
    return substantive_text or None


def _developer_instruction_text(value):
    text = _instruction_text(value)
    if text is None:
        return None
    match = _SKILLS_WRAPPER_RE.fullmatch(text)
    if match is None:
        return text
    return _skills_index_residue(match.group(1))


def _runtime_user_instruction_source(text):
    """Identify instruction-bearing user-role containers by source shape."""
    if _PROJECT_INSTRUCTIONS_RE.fullmatch(text):
        return "project"
    return next(
        (
            source
            for source, pattern in _RUNTIME_USER_INSTRUCTION_RES
            if pattern.fullmatch(text)
        ),
        None,
    )


def _is_runtime_user_context_message(payload):
    """Return whether every user-role block is known injected context."""
    content = payload.get("content")
    if not isinstance(content, list) or not content:
        return False
    for block in content:
        if not (
            isinstance(block, dict)
            and block.get("type") == "input_text"
            and isinstance(block.get("text"), str)
        ):
            return False
        text = block["text"]
        if (
            _runtime_user_instruction_source(text) is None
            and not any(
                pattern.fullmatch(text)
                for pattern in _RUNTIME_USER_CONTEXT_NOISE_RES
            )
        ):
            return False
    return True


def _user_prompt_text(text, local_images):
    if not local_images or not text.lstrip().startswith(_FILES_MENTIONED_PREFIX):
        return text
    lines = text.splitlines()
    marker_index = next(
        (
            index
            for index, line in enumerate(lines)
            if line.strip() == _USER_REQUEST_MARKER
        ),
        None,
    )
    if marker_index is None:
        return text
    wrapper_lines = set(lines[:marker_index])
    expected_file_lines = {
        "## {}: {}".format(Path(path).name, path)
        for path in local_images
        if isinstance(path, str) and path
    }
    if expected_file_lines and expected_file_lines.issubset(wrapper_lines):
        return "\n".join(lines[marker_index + 1:]).strip()
    return text


def extract_session_basic_data(records):
    """Return Codex session data available at the extraction boundary."""
    header_values = {}
    event_token_usage = None
    thread_token_usage = None
    for record in records:
        payload = record.get("payload")
        if not isinstance(payload, dict):
            continue
        if record.get("type") == "session_meta":
            for source_key, header_key in (
                ("cwd", "working_directory"),
                ("cli_version", "runtime_version"),
            ):
                value = payload.get(source_key)
                if header_key not in header_values and value not in (None, ""):
                    header_values[header_key] = value
            git_data = payload.get("git")
            if isinstance(git_data, dict) and git_data.get("branch") not in (None, ""):
                header_values.setdefault("git_branch", git_data["branch"])
        if "model" not in header_values and payload.get("model") not in (None, ""):
            header_values["model"] = payload["model"]
        if record.get("type") == "token_usage_record":
            cumulative = payload.get("thread_token_usage")
            total = (
                cumulative.get("total_tokens")
                if isinstance(cumulative, dict)
                else None
            )
            if isinstance(total, (int, float)) and not isinstance(total, bool):
                thread_token_usage = total
            continue
        if record.get("type") != "event_msg" or payload.get("type") != "token_count":
            continue
        info = payload.get("info")
        cumulative = info.get("total_token_usage") if isinstance(info, dict) else None
        total = cumulative.get("total_tokens") if isinstance(cumulative, dict) else None
        if isinstance(total, (int, float)) and not isinstance(total, bool):
            event_token_usage = total

    return session_basic_data(
        "codex",
        session_start=earliest_timestamp(records),
        token_usage=(
            thread_token_usage
            if thread_token_usage is not None
            else event_token_usage
        ),
        **header_values,
    )


def _has_progress_evidence_after(records, record_index):
    """Return whether later Codex records prove execution advanced."""
    for record in records[record_index + 1:]:
        payload = record.get("payload")
        if not isinstance(payload, dict):
            continue
        if record.get("type") == "turn_context":
            return True
        if (
            record.get("type") == "event_msg"
            and payload.get("type") in _PROGRESS_EVENT_TYPES
        ):
            return True
        if (
            record.get("type") == "response_item"
            and payload.get("type") == "message"
            and payload.get("role") in ("assistant", "user")
        ):
            return True
    return False


def _decode_json_container(value):
    if not isinstance(value, str):
        return value
    try:
        decoded = json.loads(value)
    except json.JSONDecodeError:
        return value
    return decoded if isinstance(decoded, (dict, list)) else value


def _split_view_image_result_content(content):
    """Separate images only from the known Codex view_image result shape."""
    if not isinstance(content, list):
        return content, []
    retained = []
    image_sources = []
    for block in content:
        if not isinstance(block, dict) or block.get("type") != "input_image":
            retained.append(block)
            continue
        image_url = block.get("image_url")
        match = (
            _VIEW_IMAGE_DATA_URL_RE.fullmatch(image_url)
            if isinstance(image_url, str)
            else None
        )
        if match is not None:
            image_sources.append({
                "type": "base64",
                "data": match.group(2),
                "media_type": match.group(1),
            })
            continue
        if isinstance(image_url, str) and image_url:
            image_sources.append({
                "type": "external_url",
                "url": image_url,
            })
            continue
        image_sources.append({"type": "unsupported"})
    return retained, image_sources


def _split_mcp_result_content(result):
    """Separate images from legacy wrapped or direct MCP results."""
    if not isinstance(result, dict):
        return result, []
    ok_result = result.get("Ok")
    if isinstance(ok_result, dict):
        result_container = ok_result
    else:
        result_container = result
    if not isinstance(result_container.get("content"), list):
        return result, []
    retained_content, image_sources = split_tool_result_content(
        result_container["content"],
    )
    if not image_sources:
        return result, []
    retained_result = dict(result)
    if isinstance(ok_result, dict):
        retained_ok = dict(ok_result)
        retained_ok["content"] = retained_content
        retained_result["Ok"] = retained_ok
    else:
        retained_result["content"] = retained_content
    return retained_result, image_sources


def _result_error_evidence(result):
    decoded = _decode_json_container(result)
    if not isinstance(decoded, dict):
        return None
    metadata = decoded.get("metadata")
    exit_code = metadata.get("exit_code") if isinstance(metadata, dict) else None
    if isinstance(exit_code, int) and not isinstance(exit_code, bool):
        return exit_code != 0
    if isinstance(decoded.get("success"), bool):
        return not decoded["success"]
    if "Err" in decoded:
        return True
    if "Ok" in decoded:
        return False
    return None


def _mcp_result_error_evidence(result):
    """Return error evidence from the MCP result wrapper contract."""
    decoded = _decode_json_container(result)
    if isinstance(decoded, dict):
        if isinstance(decoded.get("isError"), bool):
            return decoded["isError"]
        ok_result = decoded.get("Ok")
        if (
            isinstance(ok_result, dict)
            and isinstance(ok_result.get("isError"), bool)
        ):
            return ok_result["isError"]
    return _result_error_evidence(decoded)


def _source_lifecycle_status(payload, *, has_result=False, terminal=False):
    if has_result:
        return "complete"
    status = payload.get("status")
    if status in ("completed", "success"):
        return "complete"
    if status in ("generating", "in_progress", "running"):
        return "in_progress"
    if status in ("error", "failed"):
        return "failed"
    return "complete" if terminal else "unknown"


def _paired_lifecycle_status(records, activity):
    """Classify a paired call without overriding explicit execution state."""
    if activity.get("has_result", False):
        return "complete"
    source_status = activity["payload"].get("status")
    if source_status in ("generating", "in_progress", "running"):
        return "in_progress"
    if source_status in ("error", "failed"):
        return "failed"
    return tool_lifecycle_status(
        has_result=False,
        result_required=True,
        completion_evidenced=(
            source_status in ("completed", "success")
            or _has_progress_evidence_after(
                records,
                activity["record_index"],
            )
        ),
    )


def extract_records(records):
    """Return visible event-stream content records in source-relative order."""
    mirrors = _mirror_context(records)
    activities = []
    activities_by_payload = {}
    calls_by_source_id = {}
    results = []
    results_by_payload = {}
    for record_index, record in enumerate(records):
        payload = record.get("payload")
        if not isinstance(payload, dict):
            continue
        payload_type = payload.get("type")
        item = _completed_item(record)
        is_standalone_command = (
            item is not None
            and item.get("type") == "CommandExecution"
            and _is_standalone_command_execution(payload, mirrors)
        )
        # Extension items are self-contained. File and MCP items remain
        # first-class activities even when an outer exec call encloses them.
        is_item_activity = is_standalone_command or (
            item is not None
            and item.get("type") in ("Extension", "FileChange", "McpToolCall")
        )
        is_tool_activity = (
            record.get("type") == "response_item"
            and payload_type in (_PAIRED_CALL_TYPES | _SELF_CONTAINED_RESPONSE_TYPES)
        ) or (
            record.get("type") == "event_msg"
            and payload_type in _SELF_CONTAINED_EVENT_TYPES
        )
        if is_tool_activity or is_item_activity:
            source_payload = item if is_item_activity else payload
            activity = {
                "activity_id": "tool-{:04d}".format(len(activities) + 1),
                "record_index": record_index,
                "payload": source_payload,
            }
            activities.append(activity)
            activities_by_payload[id(source_payload)] = activity
            if (
                is_tool_activity
                and payload_type in _PAIRED_CALL_TYPES
                and payload.get("call_id")
            ):
                calls_by_source_id[payload["call_id"]] = activity
        elif (
            record.get("type") == "response_item"
            and payload_type in _PAIRED_RESULT_TYPES
        ):
            result = {"payload": payload}
            results.append(result)
            results_by_payload[id(payload)] = result

    for result in results:
        payload = result["payload"]
        activity = calls_by_source_id.get(payload.get("call_id"))
        if activity is not None:
            result["activity"] = activity
            activity["has_result"] = True
    unmatched_number = len(activities) + 1
    for result in results:
        if "activity" not in result:
            result["activity_id"] = "tool-{:04d}".format(unmatched_number)
            unmatched_number += 1

    for activity in activities:
        payload = activity["payload"]
        if payload.get("type") not in _PAIRED_CALL_TYPES:
            continue
        activity["lifecycle_status"] = _paired_lifecycle_status(
            records,
            activity,
        )

    def paired_result_record(payload):
        result_info = results_by_payload[id(payload)]
        activity = result_info.get("activity")
        if activity is None:
            activity_id = result_info["activity_id"]
            lifecycle_status = "unknown"
            lifecycle_report = unmatched_tool_result_report(activity_id)
            tool_name = "unknown"
        else:
            activity_id = activity["activity_id"]
            lifecycle_status = None
            lifecycle_report = None
            tool_name = activity["payload"].get("name", "unknown")
            if activity["payload"].get("type") == "tool_search_call":
                tool_name = "tool_search"
        raw_result = (
            payload.get("tools")
            if payload.get("type") == "tool_search_output"
            else payload.get("output")
        )
        decoded_result = _decode_json_container(raw_result)
        has_view_image_contract = (
            activity is not None
            and activity["payload"].get("type") == "function_call"
            and activity["payload"].get("name") == "view_image"
            and payload.get("type") == "function_call_output"
        )
        if has_view_image_contract:
            result, image_sources = _split_view_image_result_content(
                decoded_result,
            )
        else:
            result = decoded_result
            image_sources = []
        is_error = _result_error_evidence(raw_result)
        lifecycle_report = tool_result_report(
            activity_id,
            tool_name,
            lifecycle_report,
            is_error,
        )
        return normalized_tool_result_record(
            activity_id,
            result,
            image_sources=image_sources,
            is_error=is_error,
            lifecycle_status=lifecycle_status,
            lifecycle_report=lifecycle_report,
        )

    def paired_call_record(payload):
        activity = activities_by_payload[id(payload)]
        if payload.get("type") == "custom_tool_call":
            parameters = payload.get("input", {})
        else:
            parameters = payload.get("arguments", {})
            parameters = _decode_json_container(parameters)
        tool_name = (
            "tool_search"
            if payload.get("type") == "tool_search_call"
            else payload.get("name", "unknown")
        )
        lifecycle_status = activity["lifecycle_status"]
        record = normalized_tool_call_record(
            activity["activity_id"],
            tool_name,
            parameters,
            lifecycle_status=lifecycle_status,
            lifecycle_report=tool_lifecycle_report(
                activity["activity_id"],
                tool_name,
                lifecycle_status,
            ),
        )
        if payload.get("status") is not None:
            record["source_status"] = payload["status"]
        if (
            payload.get("type") == "tool_search_call"
            and payload.get("execution") is not None
        ):
            record["execution"] = payload["execution"]
        return record

    def self_contained_records(payload):
        activity = activities_by_payload[id(payload)]
        payload_type = payload.get("type")
        result = payload.get("result")
        has_result = result is not None
        lifecycle_status = _source_lifecycle_status(
            payload,
            has_result=has_result,
            terminal=payload_type in _SELF_CONTAINED_EVENT_TYPES,
        )
        if payload_type == "web_search_call":
            tool_name = "web_search"
            parameters = payload.get("action", {})
        elif payload_type == "view_image_tool_call":
            tool_name = "view_image"
            parameters = {"path": payload.get("path")}
        elif payload_type == "mcp_tool_call_end":
            invocation = payload.get("invocation", {})
            server = invocation.get("server", "unknown")
            tool = invocation.get("tool", "unknown")
            tool_name = "{}.{}".format(server, tool)
            parameters = invocation.get("arguments", {})
        else:
            tool_name = "image_generation"
            parameters = {"revised_prompt": payload.get("revised_prompt")}
        call_record = normalized_tool_call_record(
            activity["activity_id"],
            tool_name,
            parameters,
            result_contract="not_required",
            lifecycle_status=lifecycle_status,
            lifecycle_report=tool_lifecycle_report(
                activity["activity_id"],
                tool_name,
                lifecycle_status,
            ),
        )
        if payload.get("status") is not None:
            call_record["source_status"] = payload["status"]
        if payload.get("execution") is not None:
            call_record["execution"] = payload["execution"]
        if payload.get("duration") is not None:
            call_record["duration"] = payload["duration"]
        normalized_activity = [call_record]
        if payload_type == "mcp_tool_call_end" and "result" in payload:
            decoded_result = _decode_json_container(result)
            result_content, image_sources = _split_mcp_result_content(
                decoded_result,
            )
            is_error = _mcp_result_error_evidence(decoded_result)
            normalized_activity.append(normalized_tool_result_record(
                activity["activity_id"],
                result_content,
                image_sources=image_sources,
                is_error=is_error,
                lifecycle_report=tool_result_report(
                    activity["activity_id"],
                    tool_name,
                    None,
                    is_error,
                ),
            ))
        elif payload_type == "image_generation_call" and has_result:
            normalized_activity.append(normalized_tool_result_record(
                activity["activity_id"],
                None,
                image_sources=[{
                    "type": "base64",
                    "data": result,
                    "media_type": "image/png",
                }],
                result_available=False,
            ))
        return normalized_activity

    def extension_records(item):
        activity = activities_by_payload[id(item)]
        kind = item.get("kind")
        tool_name = _EXTENSION_TOOL_NAMES.get(kind) or kind or "extension"
        parameters = {
            key: item[key]
            for key in ("kind", "query", "action")
            if item.get(key) is not None
        }
        results = item.get("results")
        has_result = results is not None
        lifecycle_status = _source_lifecycle_status(
            item,
            has_result=has_result,
        )
        call_record = normalized_tool_call_record(
            activity["activity_id"],
            tool_name,
            parameters,
            result_contract="not_required",
            lifecycle_status=lifecycle_status,
            lifecycle_report=tool_lifecycle_report(
                activity["activity_id"],
                tool_name,
                lifecycle_status,
            ),
        )
        if item.get("status") is not None:
            call_record["source_status"] = item["status"]
        normalized_activity = [call_record]
        if has_result:
            normalized_activity.append(normalized_tool_result_record(
                activity["activity_id"],
                results,
            ))
        return normalized_activity

    def command_execution_records(item):
        activity = activities_by_payload[id(item)]
        parameters = {
            key: item[key]
            for key in ("command", "cwd")
            if item.get(key) is not None
        }
        output_keys = ("aggregated_output", "stdout", "stderr", "exit_code")
        has_output = any(item.get(key) is not None for key in output_keys)
        exit_code = item.get("exit_code")
        has_exit_evidence = (
            isinstance(exit_code, int) and not isinstance(exit_code, bool)
        )
        # Output text alone is not execution-stage evidence; only a recorded
        # exit code proves completion when the item carries no status.
        lifecycle_status = _source_lifecycle_status(
            item,
            has_result=item.get("status") is None and has_exit_evidence,
        )
        call_record = normalized_tool_call_record(
            activity["activity_id"],
            "command_execution",
            parameters,
            result_contract="not_required",
            lifecycle_status=lifecycle_status,
            lifecycle_report=tool_lifecycle_report(
                activity["activity_id"],
                "command_execution",
                lifecycle_status,
            ),
        )
        if item.get("status") is not None:
            call_record["source_status"] = item["status"]
        normalized_activity = [call_record]
        if has_output:
            is_error = exit_code != 0 if has_exit_evidence else None
            normalized_activity.append(normalized_tool_result_record(
                activity["activity_id"],
                {
                    key: item[key]
                    for key in output_keys
                    if item.get(key) is not None
                },
                is_error=is_error,
                lifecycle_report=tool_result_report(
                    activity["activity_id"],
                    "command_execution",
                    None,
                    is_error,
                ),
            ))
        return normalized_activity

    def file_change_records(item):
        activity = activities_by_payload[id(item)]
        lifecycle_status = _source_lifecycle_status(item, terminal=True)
        call_record = normalized_tool_call_record(
            activity["activity_id"],
            "file_change",
            {"changes": item.get("changes", {})},
            result_contract="not_required",
            lifecycle_status=lifecycle_status,
            lifecycle_report=tool_lifecycle_report(
                activity["activity_id"],
                "file_change",
                lifecycle_status,
            ),
        )
        for key in ("status", "auto_approved", "duration"):
            if item.get(key) is not None:
                output_key = "source_status" if key == "status" else key
                call_record[output_key] = item[key]
        normalized_activity = [call_record]
        output_keys = ("stdout", "stderr")
        if any(item.get(key) is not None for key in output_keys):
            is_error = item.get("status") == "failed"
            normalized_activity.append(normalized_tool_result_record(
                activity["activity_id"],
                {
                    key: item[key]
                    for key in output_keys
                    if item.get(key) is not None
                },
                is_error=is_error,
                lifecycle_report=tool_result_report(
                    activity["activity_id"],
                    "file_change",
                    None,
                    is_error,
                ),
            ))
        return normalized_activity

    def mcp_tool_call_item_records(item):
        activity = activities_by_payload[id(item)]
        lifecycle_status = _source_lifecycle_status(
            item,
            terminal=True,
        )
        tool_name = "{}.{}".format(item["server"], item["tool"])
        call_record = normalized_tool_call_record(
            activity["activity_id"],
            tool_name,
            item.get("arguments"),
            result_contract="not_required",
            lifecycle_status=lifecycle_status,
            lifecycle_report=tool_lifecycle_report(
                activity["activity_id"],
                tool_name,
                lifecycle_status,
            ),
        )
        if item.get("status") is not None:
            call_record["source_status"] = item["status"]
        for key in (
            "duration",
            "connector_id",
            "mcp_app_resource_uri",
            "link_id",
            "app_name",
            "action_name",
            "plugin_id",
            "read_only_hint",
        ):
            if item.get(key) is not None:
                call_record[key] = item[key]
        normalized_activity = [call_record]
        if "result" in item:
            decoded_result = _decode_json_container(item.get("result"))
            result, image_sources = _split_mcp_result_content(decoded_result)
            is_error = _mcp_result_error_evidence(decoded_result)
            if item.get("status") in ("error", "failed"):
                is_error = True
            normalized_activity.append(normalized_tool_result_record(
                activity["activity_id"],
                result,
                image_sources=image_sources,
                is_error=is_error,
                lifecycle_report=tool_result_report(
                    activity["activity_id"],
                    tool_name,
                    None,
                    is_error,
                ),
            ))
        elif item.get("error") is not None:
            normalized_activity.append(normalized_tool_result_record(
                activity["activity_id"],
                {"error": item["error"]},
                is_error=True,
                lifecycle_report=tool_result_report(
                    activity["activity_id"],
                    tool_name,
                    None,
                    True,
                ),
            ))
        return normalized_activity

    normalized = []
    seen_instructions = set()
    submitted_user_messages = set()
    item_reasoning_texts = {}
    for record in records:
        payload = record.get("payload")
        if (
            record.get("type") == "event_msg"
            and isinstance(payload, dict)
            and payload.get("type") == "user_message"
            and isinstance(payload.get("message"), str)
        ):
            submitted_user_messages.add(payload["message"])
        item = _completed_item(record)
        if item is None:
            continue
        if item.get("type") == "UserMessage":
            text = _content_blocks_text(item)
            if text:
                submitted_user_messages.add(text)
        elif item.get("type") == "Reasoning" and item.get("id"):
            text = _reasoning_item_summary_text(item)
            if text:
                item_reasoning_texts[item["id"]] = text

    def append_instruction(source, text):
        identity = (source, text)
        if identity in seen_instructions:
            return
        seen_instructions.add(identity)
        normalized.append(normalized_agent_instructions_record(source, text))

    reasoning_number = 0
    for record in records:
        payload = record.get("payload")
        if not isinstance(payload, dict):
            continue
        payload_type = payload.get("type")
        if record.get("type") == "session_meta":
            base_instructions = _instruction_text(
                payload.get("base_instructions"),
            )
            if base_instructions:
                append_instruction(
                    "system",
                    base_instructions,
                )
        elif record.get("type") == "world_state":
            state = payload.get("state")
            if not isinstance(state, dict):
                continue
            agents_md_text = _instruction_text(state.get("agents_md"))
            if agents_md_text:
                append_instruction("project", agents_md_text)
            host_skills = state.get("host_skills")
            host_skills_body = (
                host_skills.get("body")
                if isinstance(host_skills, dict)
                else None
            )
            if isinstance(host_skills_body, str):
                # Other world_state "instructions" fields hold content digests,
                # not instruction text, so only these two subtrees qualify.
                residue = _skills_index_residue(host_skills_body)
                if residue:
                    append_instruction("runtime", residue)
        elif (
            record.get("type") == "response_item"
            and payload_type == "agent_message"
        ):
            text = _content_blocks_text(payload)
            if text.strip():
                instruction = normalized_agent_instructions_record("agent", text)
                for key in ("author", "recipient"):
                    if isinstance(payload.get(key), str) and payload[key]:
                        instruction[key] = payload[key]
                # Inter-agent messages legitimately repeat, so they bypass the
                # re-injection dedup that append_instruction applies.
                normalized.append(instruction)
        elif (
            record.get("type") == "response_item"
            and payload_type == "message"
            and payload.get("role") in ("developer", "system")
        ):
            content = payload.get("content")
            if not isinstance(content, list):
                continue
            for block in content:
                if not isinstance(block, dict) or block.get("type") != "input_text":
                    continue
                text = _developer_instruction_text(block.get("text"))
                if text:
                    append_instruction(
                        payload["role"],
                        text,
                    )
        elif (
            record.get("type") == "response_item"
            and payload_type == "message"
            and payload.get("role") == "user"
        ):
            content = payload.get("content")
            if not isinstance(content, list):
                continue
            for block in content:
                if not isinstance(block, dict) or block.get("type") != "input_text":
                    continue
                text = _instruction_text(block.get("text"))
                if text is None or text in submitted_user_messages:
                    continue
                source = _runtime_user_instruction_source(text)
                if source is not None:
                    append_instruction(source, text)
        elif record.get("type") == "response_item" and payload_type == "reasoning":
            summary_text = (
                _reasoning_summary_text(payload)
                or item_reasoning_texts.get(payload.get("id"), "")
            )
            if summary_text:
                reasoning_number += 1
                normalized.append(normalized_reasoning_record(
                    "summary",
                    text=summary_text,
                    sequence_number=reasoning_number,
                ))
        elif (
            record.get("type") == "event_msg"
            and payload_type in _TURN_LIFECYCLE_EVENTS
        ):
            event, detail_keys = _TURN_LIFECYCLE_EVENTS[payload_type]
            normalized.append(normalized_turn_lifecycle_record(
                event,
                **{key: payload.get(key) for key in detail_keys},
            ))
        elif (
            record.get("type") == "event_msg"
            and payload_type in _EVENT_CONTENT_CATEGORIES
        ):
            content_category = _EVENT_CONTENT_CATEGORIES[payload_type]
            text = payload.get("message")
            if not isinstance(text, str):
                continue
            local_images = payload.get("local_images", [])
            external_images = payload.get("images", [])
            image_sources = [
                {"type": "path", "path": path}
                for path in local_images
                if isinstance(path, str) and path
            ]
            image_sources.extend(
                {"type": "external_url", "url": url}
                for url in external_images
                if isinstance(url, str) and url
            )
            if content_category == "user_prompt" and image_sources:
                text = _user_prompt_text(text, local_images)
            if text.strip() or image_sources:
                normalized.append(normalized_content_record(
                    content_category,
                    text=text,
                    image_sources=image_sources,
                ))
        elif (
            record.get("type") == "event_msg"
            and payload_type == "item_completed"
        ):
            item = payload.get("item")
            if not isinstance(item, dict):
                continue
            item_type = item.get("type")
            if item_type in _ITEM_MESSAGE_CATEGORIES:
                text = _content_blocks_text(item)
                if text.strip():
                    normalized.append(normalized_content_record(
                        _ITEM_MESSAGE_CATEGORIES[item_type],
                        text=text,
                    ))
            elif item_type == "Reasoning":
                # A Reasoning item paired by id only mirrors the response_item
                # reasoning entity this adapter already extracts or counts.
                if item.get("id") not in mirrors["reasoning_ids"]:
                    summary_text = _reasoning_item_summary_text(item)
                    if summary_text:
                        reasoning_number += 1
                        normalized.append(normalized_reasoning_record(
                            "summary",
                            text=summary_text,
                            sequence_number=reasoning_number,
                        ))
            elif item_type == "Extension":
                normalized.extend(extension_records(item))
            elif item_type == "FileChange":
                normalized.extend(file_change_records(item))
            elif item_type == "McpToolCall":
                normalized.extend(mcp_tool_call_item_records(item))
            elif (
                item_type == "CommandExecution"
                # Registered in the activity pass only when it stands alone;
                # otherwise it is the exec tool-call stream's display copy.
                and id(item) in activities_by_payload
            ):
                normalized.extend(command_execution_records(item))
        elif (
            record.get("type") == "response_item"
            and payload_type in _PAIRED_CALL_TYPES
        ):
            normalized.append(paired_call_record(payload))
        elif (
            record.get("type") == "response_item"
            and payload_type in _PAIRED_RESULT_TYPES
        ):
            normalized.append(paired_result_record(payload))
        elif (
            record.get("type") == "response_item"
            and payload_type in _SELF_CONTAINED_RESPONSE_TYPES
        ) or (
            record.get("type") == "event_msg"
            and payload_type in _SELF_CONTAINED_EVENT_TYPES
        ):
            normalized.extend(self_contained_records(payload))
    return normalized
