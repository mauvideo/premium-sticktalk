from scripts.story_director import CauHinh, tao_cau_chuyen
from scripts.story_timing import estimate_duration_seconds, target_word_count, word_count

VISUAL_KEYS = {
    "background", "mainCharacter", "secondaryObjects", "icons", "paperElements", "camera", "transition",
    "highlight", "mood", "colorPalette", "composition",
}

def test_target_word_count_matches_requested_duration_examples():
    assert 80 <= target_word_count(30) <= 90
    assert 165 <= target_word_count(60) <= 180
    assert 250 <= target_word_count(90) <= 270
    assert 500 <= target_word_count(180) <= 540

def test_story_timing_fits_30_60_90_within_two_seconds():
    for duration in (30, 60, 90):
        story = tao_cau_chuyen(CauHinh("Hành trình vượt qua thất bại", duration, che_do="ke_chuyen"))
        estimated = estimate_duration_seconds(sum(word_count(scene["narration"]) for scene in story["scenes"]))
        assert abs(estimated - duration) <= 2.0
        assert story["timing"]["withinTolerance"]
        assert story["targetWordCount"] == story["timing"]["targetWordCount"]

def test_story_timing_supports_180_seconds():
    story = tao_cau_chuyen(CauHinh("Hành trình vượt qua thất bại", 180, che_do="ke_chuyen"))
    assert abs(story["estimatedDuration"] - 180) <= 2.0
    assert story["timing"]["actualWordCount"] >= 500

def test_visual_plan_has_required_layers_and_diverse_composition():
    story = tao_cau_chuyen(CauHinh("Một chủ cửa hàng vượt qua thất bại", 60, che_do="ke_chuyen"))
    compositions = []
    for scene in story["scenes"]:
        plan = scene["visualPlan"]
        assert VISUAL_KEYS <= plan.keys()
        assert plan["background"]
        assert plan["mainCharacter"]
        assert plan["secondaryObjects"]
        assert plan["icons"] or plan["paperElements"]
        compositions.append(plan["composition"])
    assert len(compositions) == len(set(compositions))
    assert len({scene["visualPlan"]["background"] for scene in story["scenes"]}) > 1
    assert len({scene["visualPlan"]["camera"] for scene in story["scenes"]}) > 1
