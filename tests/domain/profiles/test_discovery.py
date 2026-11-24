import logging

from voice_clone.domain.profiles.discovery import discover_profiles


def _make_voice(root, name, files):
    folder = root / name
    folder.mkdir()
    for file_name in files:
        (folder / file_name).write_bytes(b"x")
    return folder


def test_discovers_profiles_sorted_by_name_with_index(tmp_path):
    _make_voice(tmp_path, "zed", ["model.pth"])
    _make_voice(tmp_path, "alpha", ["model.pth", "added.index"])

    profiles = discover_profiles(tmp_path)

    assert [p.name for p in profiles] == ["alpha", "zed"]
    assert profiles[0].index_path == tmp_path / "alpha" / "added.index"
    assert profiles[1].index_path is None


def test_missing_voices_folder_returns_empty_list(tmp_path):
    assert discover_profiles(tmp_path / "nope") == []


def test_folder_without_pth_is_skipped(tmp_path):
    _make_voice(tmp_path, "empty", ["notes.txt"])

    assert discover_profiles(tmp_path) == []


def test_loose_files_in_voices_folder_are_ignored(tmp_path):
    (tmp_path / "stray.pth").write_bytes(b"x")

    assert discover_profiles(tmp_path) == []


def test_several_pth_files_use_first_by_name_and_warn(tmp_path, caplog):
    _make_voice(tmp_path, "multi", ["b.pth", "a.pth"])

    with caplog.at_level(logging.WARNING):
        profiles = discover_profiles(tmp_path)

    assert profiles[0].model_path.name == "a.pth"
    assert "2 .pth files" in caplog.text
