"""
tests/test_files.py
--------------------
Exercises tools/files.py against a temp directory. Never touches
real user files.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from tools import files


@pytest.fixture
def tmp_workspace(tmp_path):
    return tmp_path


def test_create_and_read_file(tmp_workspace):
    target = tmp_workspace / "note.txt"
    result = files.create_file(str(target), content="hello shadow")
    assert result["success"] is True
    assert target.read_text() == "hello shadow"

    read_result = files.read_file(str(target))
    assert read_result["success"] is True
    assert read_result["content"] == "hello shadow"


def test_create_file_refuses_overwrite(tmp_workspace):
    target = tmp_workspace / "note.txt"
    target.write_text("original")
    result = files.create_file(str(target), content="overwrite attempt")
    assert result["success"] is False
    assert target.read_text() == "original"


def test_create_folder(tmp_workspace):
    target = tmp_workspace / "nested" / "folder"
    result = files.create_folder(str(target))
    assert result["success"] is True
    assert target.is_dir()


def test_search_files(tmp_workspace):
    (tmp_workspace / "a.pdf").write_text("x")
    (tmp_workspace / "b.pdf").write_text("x")
    (tmp_workspace / "c.txt").write_text("x")

    result = files.search_files(str(tmp_workspace), pattern="*.pdf")
    assert result["success"] is True
    assert len(result["results"]) == 2


def test_move_file(tmp_workspace):
    src = tmp_workspace / "source.txt"
    src.write_text("data")
    dst = tmp_workspace / "moved" / "source.txt"

    result = files.move_file(str(src), str(dst))
    assert result["success"] is True
    assert not src.exists()
    assert dst.read_text() == "data"


def test_move_file_refuses_overwrite(tmp_workspace):
    src = tmp_workspace / "source.txt"
    src.write_text("data")
    dst = tmp_workspace / "existing.txt"
    dst.write_text("already here")

    result = files.move_file(str(src), str(dst))
    assert result["success"] is False
    assert dst.read_text() == "already here"


def test_copy_file(tmp_workspace):
    src = tmp_workspace / "source.txt"
    src.write_text("data")
    dst = tmp_workspace / "copy.txt"

    result = files.copy_file(str(src), str(dst))
    assert result["success"] is True
    assert src.exists()
    assert dst.read_text() == "data"


def test_rename_file(tmp_workspace):
    src = tmp_workspace / "old.txt"
    src.write_text("data")

    result = files.rename_file(str(src), "new.txt")
    assert result["success"] is True
    assert (tmp_workspace / "new.txt").exists()
    assert not src.exists()


def test_delete_file_requires_confirmation(tmp_workspace):
    target = tmp_workspace / "delete_me.txt"
    target.write_text("data")

    unconfirmed = files.delete_file(str(target), confirmed=False)
    assert unconfirmed["success"] is False
    assert target.exists()

    confirmed = files.delete_file(str(target), confirmed=True)
    assert confirmed["success"] is True
    assert not target.exists()


def test_delete_folder_with_confirmation(tmp_workspace):
    target = tmp_workspace / "nested" / "to_delete"
    target.mkdir(parents=True)
    (target / "file.txt").write_text("data")

    unconfirmed = files.delete_folder(str(target), confirmed=False)
    assert unconfirmed["success"] is False
    assert target.exists()

    confirmed = files.delete_folder(str(target), confirmed=True)
    assert confirmed["success"] is True
    assert not target.exists()


def test_delete_folder_refuses_shallow_paths():
    # A path with very few parts (e.g. "/" or "C:\Users") must be refused
    # even if 'confirmed' is True, as a hard guardrail against wiping
    # top-level system directories.
    result = files.delete_folder("/", confirmed=True)
    assert result["success"] is False


def test_delete_missing_file(tmp_workspace):
    missing = tmp_workspace / "does_not_exist.txt"
    result = files.delete_file(str(missing), confirmed=True)
    assert result["success"] is False
