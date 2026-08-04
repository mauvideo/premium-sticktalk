import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_v3_story_is_configurable_and_varied(tmp_path):
    subprocess.run(
        [sys.executable, str(ROOT / "scripts/generate_story.py"), "--idea", "test",
         "--duration", "30", "--style", "người_que_tiktok", "--motion-level", "viral_tiktok"],
        cwd=tmp_path, check=True,
    )
    story = json.loads((tmp_path / "assets/story.json").read_text(encoding="utf-8"))
    assert story["version"] == 3
    assert story["style"] == "tiktok"
    assert story["motionLevel"] == "viral"
    assert round(sum(scene["duration"] for scene in story["scenes"]), 1) == 30
    assert len({scene["camera"]["type"] for scene in story["scenes"]}) == len(story["scenes"])
    assert all({"speed", "easing", "strength", "duration"} <= scene["camera"].keys() for scene in story["scenes"])
    assert all({"emotion", "gesture", "zoom", "subtitleAnimation"} <= scene.keys() for scene in story["scenes"])
