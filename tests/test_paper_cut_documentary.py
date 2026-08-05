import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_template_registered_in_remotion_router():
    sticktalk = (ROOT / "remotion/src/StickTalkVideo.tsx").read_text(encoding="utf-8")
    template = (ROOT / "remotion/src/templates/paper-cut-documentary/index.tsx").read_text(encoding="utf-8")
    assert "PaperCutDocumentaryScene" in sticktalk
    assert "isPaperCutDocumentaryTemplate(extended.template)" in sticktalk
    assert "paper-cut-documentary" in template


def test_workflow_maps_vietnamese_name_to_internal_id():
    workflow = (ROOT / ".github/workflows/create-sticktalk-video.yml").read_text(encoding="utf-8")
    assert '"Cắt giấy tài liệu"' in workflow
    assert "inputs.template == 'Cắt giấy tài liệu' && 'paper-cut-documentary'" in workflow


def test_template_metadata_is_available():
    data = json.loads((ROOT / "projects/motivation/templates.json").read_text(encoding="utf-8"))
    item = next(t for t in data["templates"] if t["id"] == "paper-cut-documentary")
    assert item["name"] == "Cắt giấy tài liệu"
    assert item["license"]


def test_three_scene_fixture_with_missing_image_and_vietnamese_text():
    story = json.loads((ROOT / "tests/fixtures/paper_cut_story.json").read_text(encoding="utf-8"))
    assert story["template"] == "paper-cut-documentary"
    assert len(story["scenes"]) == 3
    assert any("image" not in scene for scene in story["scenes"])
    assert "tiếng Việt có dấu" in story["title"]


def test_vieneu_tts_files_not_modified_by_template_change():
    changed = {line.strip() for line in __import__('subprocess').check_output(['git','diff','--name-only'], cwd=ROOT, text=True).splitlines()}
    forbidden = {'scripts/generate_tts.py'}
    assert not (changed & forbidden)
    assert not any(path.startswith('scripts/tts/') for path in changed)
