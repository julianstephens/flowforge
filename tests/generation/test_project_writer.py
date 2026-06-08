from pathlib import Path

import pytest

from flowforge.generation.models import GeneratedFile
from flowforge.generation.project_writer import FileAlreadyExistsError, ProjectWriter


def _make_file(
    path: Path, content: str = "content", overwrite: bool = False
) -> GeneratedFile:
    return GeneratedFile(path=path, content=content, overwrite=overwrite)


class TestFileAlreadyExistsError:
    def test_stores_path(self):
        err = FileAlreadyExistsError("some/file.tf")
        assert err.path == "some/file.tf"

    def test_message_includes_path(self):
        err = FileAlreadyExistsError("some/file.tf")
        assert "some/file.tf" in str(err)

    def test_is_file_exists_error(self):
        assert isinstance(FileAlreadyExistsError("x"), FileExistsError)


class TestProjectWriter:
    def test_writes_file_content(self, tmp_path):
        target = tmp_path / "out" / "main.tf"
        files = [_make_file(target, "hello world")]
        ProjectWriter().write(files)
        assert target.read_text() == "hello world"

    def test_creates_parent_directories(self, tmp_path):
        target = tmp_path / "a" / "b" / "c" / "file.tf"
        ProjectWriter().write([_make_file(target)])
        assert target.exists()

    def test_writes_multiple_files(self, tmp_path):
        files = [
            _make_file(tmp_path / "a.tf", "aaa"),
            _make_file(tmp_path / "b.tf", "bbb"),
        ]
        ProjectWriter().write(files)
        assert (tmp_path / "a.tf").read_text() == "aaa"
        assert (tmp_path / "b.tf").read_text() == "bbb"

    def test_empty_list_does_nothing(self, tmp_path):
        ProjectWriter().write([])
        assert list(tmp_path.iterdir()) == []

    def test_raises_when_file_exists_and_no_overwrite(self, tmp_path):
        target = tmp_path / "file.tf"
        target.write_text("original")
        with pytest.raises(FileAlreadyExistsError) as exc_info:
            ProjectWriter().write([_make_file(target, "new content")])
        assert exc_info.value.path == str(target)

    def test_existing_file_not_modified_when_overwrite_false(self, tmp_path):
        target = tmp_path / "file.tf"
        target.write_text("original")
        with pytest.raises(FileAlreadyExistsError):
            ProjectWriter().write([_make_file(target, "new content", overwrite=False)])
        assert target.read_text() == "original"

    def test_overwrites_file_when_overwrite_true(self, tmp_path):
        target = tmp_path / "file.tf"
        target.write_text("original")
        ProjectWriter().write([_make_file(target, "updated", overwrite=True)])
        assert target.read_text() == "updated"

    def test_new_file_written_regardless_of_overwrite_flag(self, tmp_path):
        target = tmp_path / "new.tf"
        ProjectWriter().write([_make_file(target, "fresh", overwrite=False)])
        assert target.read_text() == "fresh"

    def test_raises_on_first_conflicting_file(self, tmp_path):
        existing = tmp_path / "exists.tf"
        existing.write_text("old")
        files = [
            _make_file(tmp_path / "new.tf", "ok"),
            _make_file(existing, "conflict"),
        ]
        with pytest.raises(FileAlreadyExistsError):
            ProjectWriter().write(files)

    def test_files_before_conflict_are_written(self, tmp_path):
        existing = tmp_path / "exists.tf"
        existing.write_text("old")
        new_file = tmp_path / "new.tf"
        files = [
            _make_file(new_file, "ok"),
            _make_file(existing, "conflict"),
        ]
        with pytest.raises(FileAlreadyExistsError):
            ProjectWriter().write(files)
        assert new_file.read_text() == "ok"
