from scripts.story_director import CauHinh, tao_cau_chuyen
from scripts.story_similarity import combined_similarity, too_similar

REQUIRED = ["sceneRole", "storyProgress", "imageFocus", "dramaticLevel"]
BANNED_HOOK_PREFIXES = ("hôm nay", "bạn có biết", "hãy")

def test_story_engine_assigns_story_arc_fields_and_non_banned_hook():
    story = tao_cau_chuyen(CauHinh("Đừng bỏ cuộc khi cửa hàng nhỏ gặp khó", 45, che_do="ke_chuyen"))
    scenes = story["scenes"]
    assert scenes[0]["sceneRole"] == "Hook"
    assert scenes[-1]["sceneRole"] == "Lesson"
    assert {"Context", "Conflict", "Development", "Turning Point"} <= {scene["sceneRole"] for scene in scenes}
    assert all(set(REQUIRED) <= scene.keys() for scene in scenes)
    assert not scenes[0]["narration"].casefold().startswith(BANNED_HOOK_PREFIXES)
    assert len({scene["imageFocus"] for scene in scenes}) > 3

def test_story_engine_reduces_repeated_scene_ideas_below_threshold():
    story = tao_cau_chuyen(CauHinh("Đừng bỏ cuộc", 45, che_do="ke_chuyen"))
    narrations = [scene["narration"] for scene in story["scenes"]]
    for i, current in enumerate(narrations):
        for previous in narrations[:i]:
            assert not too_similar(current, previous), combined_similarity(current, previous)

def test_similarity_module_reports_keyword_cosine_and_semantic_scores():
    scores = combined_similarity("Đừng bỏ cuộc, hãy kiên trì", "Đừng từ bỏ, hãy cố gắng")
    assert {"keywordOverlap", "cosineSimilarity", "semanticSimilarity", "combinedSimilarity"} <= scores.keys()
    assert scores["combinedSimilarity"] > 0.2
