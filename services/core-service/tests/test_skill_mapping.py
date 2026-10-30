from app.services.cv_utils import map_skill_names, match_skill_names

TAX = [
    {"id": 1, "name": "React", "aliases": ["ReactJS"], "category": "Frontend"},
    {"id": 2, "name": "Node.js", "aliases": [], "category": "Backend"},
    {"id": 3, "name": "C#", "aliases": ["CSharp"], "category": "Ngôn ngữ lập trình"},
]


def test_map_alias_compact_and_dedupe():
    matched, unmapped = map_skill_names(["react js", "NodeJS", "react", "Cobol", "  "], TAX)
    assert [m["id"] for m in matched] == [1, 2]          # không trùng, giữ thứ tự
    assert matched[0] == {"id": 1, "name": "React", "category": "Frontend"}
    assert unmapped == ["Cobol"]


def test_canonical_beats_alias_and_special_chars():
    matched, _ = map_skill_names(["c#", "CSharp"], TAX)
    assert [m["id"] for m in matched] == [3]


def test_backward_compatible_wrapper():
    assert [m["name"] for m in match_skill_names(["ReactJS"], TAX)] == ["React"]
