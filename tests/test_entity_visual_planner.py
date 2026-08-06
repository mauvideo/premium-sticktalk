import json

from scripts.entity_visual_planner import build_search_queries, classify_main_entity, plan_entities


def sample_story(topic):
    return {
        "title": topic,
        "scenes": [
            {"headline": "Khởi đầu", "narration": f"Năm 1911, {topic} bắt đầu hành trình tại Việt Nam."},
            {"headline": "Bước ngoặt", "narration": f"Đến năm 1954, câu chuyện của {topic} bước sang một giai đoạn mới."},
        ],
    }


def test_planner_is_topic_agnostic_and_populates_scene_contract():
    first = plan_entities(sample_story("Nhân vật Alpha"))
    second = plan_entities(sample_story("Nhân vật Beta"))
    assert first["entityVisualPlan"]["mainEntity"] == "Nhân vật Alpha"
    assert second["entityVisualPlan"]["mainEntity"] == "Nhân vật Beta"
    assert first["entityVisualPlan"]["archivalSearchTerms"] != second["entityVisualPlan"]["archivalSearchTerms"]
    required = {"mainSubject", "supportingSubjects", "location", "timePeriod", "event", "visualEvidence", "searchQueries", "assetRoles"}
    for scene in first["scenes"]:
        assert required <= scene["entityVisualPlan"].keys()
        assert len(scene["entityVisualPlan"]["assetRoles"]) >= 7
        assert scene["visualPlan"]["mainCharacter"] == "Nhân vật Alpha"
        assert scene["visualPlan"]["dataLayers"]


def test_queries_are_bilingual_and_restrict_sources():
    queries = build_search_queries("Nguyễn Văn A", "Sự kiện B", "Hà Nội", ["radio"])
    text = " ".join(queries)
    assert "chân dung" in text and "portrait" in text
    assert "Wikimedia Commons" in text and "Openverse" in text
    assert "Google Images" not in text


def test_person_and_explanatory_topics_do_not_share_portrait_strategy():
    assert classify_main_entity("Steve Jobs") == "person"
    assert classify_main_entity("Cách Internet hoạt động") == "concept"
    assert classify_main_entity("Vì sao máy bay bay được") == "concept"
    concept = plan_entities(sample_story("Cách Internet hoạt động"))
    queries = " ".join(concept["entityVisualPlan"]["archivalSearchTerms"])
    assert concept["entityVisualPlan"]["mainEntityType"] == "concept"
    assert "explanatory diagram" in queries
    assert "portrait" not in queries


def test_plan_serializes_to_manifest_ready_json():
    encoded = json.dumps(plan_entities(sample_story("Một phát minh khoa học")), ensure_ascii=False)
    assert "mapsNeeded" in encoded and "chartsNeeded" in encoded
