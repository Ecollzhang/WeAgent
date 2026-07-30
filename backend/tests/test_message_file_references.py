from app.services.message_element_builder import mentioned_file_elements
from app.services.message_service import (
    MessageService,
    _repair_legacy_json_file_elements,
)


def test_json_workspace_reference_is_not_truncated_to_javascript_extension():
    path = "/workspace/agents/课件制作师/slide_document.json"

    summary = MessageService._display_summary_from_raw(
        f"课件已生成：`{path}`"
    )
    elements = mentioned_file_elements("conversation-1", f"文件：`{path}`")

    assert path in summary
    assert "slide_document.js`" not in summary
    assert [element["data"]["path"] for element in elements] == [path]


def test_legacy_javascript_file_card_is_repaired_when_raw_output_names_json():
    elements = [
        {
            "type": "file",
            "content": "slide_document.js",
            "data": {
                "name": "slide_document.js",
                "path": "/workspace/agents/courseware/slide_document.js",
                "url": "/api/sandbox/sessions/c1/workspace/agents/courseware/slide_document.js",
            },
        }
    ]

    changed = _repair_legacy_json_file_elements(
        elements,
        "Created `/workspace/agents/courseware/slide_document.json`.",
    )

    assert changed is True
    assert elements[0]["content"] == "slide_document.json"
    assert elements[0]["data"]["name"] == "slide_document.json"
    assert elements[0]["data"]["path"].endswith("slide_document.json")
    assert elements[0]["data"]["url"].endswith("slide_document.json")
