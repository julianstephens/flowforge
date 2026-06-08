from pathlib import Path

import pytest

from flowforge.generation.models import GeneratedFile, WriterResult
from flowforge.generation.project_writer import (
    InvalidFilePathCode,
    InvalidFilePathError,
    MissingTargetDirectoryError,
    ProjectWriter,
)


def _make_file(
    path: Path, content: str = "content", overwrite: bool = False
) -> GeneratedFile:
    return GeneratedFile(path=path, content=content, overwrite=overwrite)


class TestInvalidFilePathError:
    def test_stores_path_and_code(self):
        path = Path("some/file.tf")
        err = InvalidFilePathError(path, InvalidFilePathCode.ABSOLUTE_PATH)
        assert err.path == path
        assert err.code == InvalidFilePathCode.ABSOLUTE_PATH

    def test_absolute_path_message(self):
        err = InvalidFilePathError(
            Path("/abs/file.tf"), InvalidFilePathCode.ABSOLUTE_PATH
        )
        assert "relative" in str(err).lower()

    def test_path_traversal_message(self):
        err = InvalidFilePathError(
            Path("../file.tf"), InvalidFilePathCode.PATH_TRAVERSAL
        )
        assert "traversal" in str(err).lower()

    def test_is_project_writer_error(self):
        from flowforge.generation.project_writer import ProjectWriterError

        assert isinstance(
            InvalidFilePathError(Path("x"), InvalidFilePathCode.ABSOLUTE_PATH),
            ProjectWriterError,
        )


class TestProjectWriter:
    def test_returns_writer_result(self, tmp_path):
        result = ProjectWriter.write(tmp_path, [_make_file(Path("file.tf"))])
        assert isinstance(result, WriterResult)

    def test_writes_file_content(self, tmp_path):
        ProjectWriter.write(tmp_path, [_make_file(Path("main.tf"), "hello world")])
        assert (tmp_path / "main.tf").read_text() == "hello world"

    def test_creates_parent_directories(self, tmp_path):
        ProjectWriter.write(tmp_path, [_make_file(Path("a/b/c/file.tf"))])
        assert (tmp_path / "a" / "b" / "c" / "file.tf").exists()

    def test_written_file_appears_in_written_files(self, tmp_path):
        file = _make_file(Path("file.tf"))
        result = ProjectWriter.write(tmp_path, [file])
        assert file in result.written_files
        assert result.skipped_files == []
        assert result.errors == {}

    def test_writes_multiple_files(self, tmp_path):
        files = [
            _make_file(Path("a.tf"), "aaa"),
            _make_file(Path("b.tf"), "bbb"),
        ]
        result = ProjectWriter.write(tmp_path, files)
        assert (tmp_path / "a.tf").read_text() == "aaa"
        assert (tmp_path / "b.tf").read_text() == "bbb"
        assert len(result.written_files) == 2

    def test_empty_list_returns_empty_result(self, tmp_path):
        result = ProjectWriter.write(tmp_path, [])
        assert result.written_files == []
        assert result.skipped_files == []
        assert result.errors == {}

    def test_existing_file_skipped_when_overwrite_false(self, tmp_path):
        (tmp_path / "file.tf").write_text("original")
        file = _make_file(Path("file.tf"), "new content", overwrite=False)
        result = ProjectWriter.write(tmp_path, [file])
        assert file in result.skipped_files
        assert result.written_files == []
        assert (tmp_path / "file.tf").read_text() == "original"

    def test_existing_file_overwritten_when_overwrite_true(self, tmp_path):
        (tmp_path / "file.tf").write_text("original")
        file = _make_file(Path("file.tf"), "updated", overwrite=True)
        result = ProjectWriter.write(tmp_path, [file])
        assert file in result.written_files
        assert result.skipped_files == []
        assert (tmp_path / "file.tf").read_text() == "updated"

    def test_new_file_written_regardless_of_overwrite_flag(self, tmp_path):
        file = _make_file(Path("new.tf"), "fresh", overwrite=False)
        result = ProjectWriter.write(tmp_path, [file])
        assert (tmp_path / "new.tf").read_text() == "fresh"
        assert file in result.written_files

    def test_processing_continues_after_skip(self, tmp_path):
        (tmp_path / "exists.tf").write_text("old")
        skipped = _make_file(Path("exists.tf"), "conflict", overwrite=False)
        written = _make_file(Path("new.tf"), "ok")
        result = ProjectWriter.write(tmp_path, [skipped, written])
        assert skipped in result.skipped_files
        assert written in result.written_files
        assert (tmp_path / "new.tf").read_text() == "ok"

    def test_write_error_collected_not_raised(self, tmp_path):
        file = _make_file(Path("file.tf"), "content")
        original_write_text = Path.write_text

        def raise_on_write(_self, *_args, **_kwargs):
            raise OSError("disk full")

        Path.write_text = raise_on_write
        try:
            result = ProjectWriter.write(tmp_path, [file])
        finally:
            Path.write_text = original_write_text

        expected_path = str(tmp_path.resolve() / "file.tf")
        assert expected_path in result.errors
        assert isinstance(result.errors[expected_path], OSError)
        assert result.written_files == []

    def test_processing_continues_after_write_error(self, tmp_path):
        files = [_make_file(Path("first.tf"), "a"), _make_file(Path("second.tf"), "b")]
        call_count = 0
        original_write_text = Path.write_text

        def fail_first(self, *args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise OSError("disk full")
            return original_write_text(self, *args, **kwargs)

        Path.write_text = fail_first
        try:
            result = ProjectWriter.write(tmp_path, files)
        finally:
            Path.write_text = original_write_text

        assert str(tmp_path.resolve() / "first.tf") in result.errors
        assert files[1] in result.written_files
        assert (tmp_path / "second.tf").read_text() == "b"

    def test_missing_target_directory_raises(self, tmp_path):
        target_dir = tmp_path / "nonexistent"
        file = _make_file(Path("file.tf"))
        with pytest.raises(MissingTargetDirectoryError) as exc_info:
            ProjectWriter.write(target_dir, [file])
        assert exc_info.value.target_dir == target_dir

    def test_missing_target_directory_message(self, tmp_path):
        target_dir = tmp_path / "nonexistent"
        with pytest.raises(MissingTargetDirectoryError) as exc_info:
            ProjectWriter.write(target_dir, [_make_file(Path("file.tf"))])
        assert str(target_dir) in str(exc_info.value)

    def test_missing_target_directory_is_project_writer_error(self, tmp_path):
        from flowforge.generation.project_writer import ProjectWriterError

        target_dir = tmp_path / "nonexistent"
        with pytest.raises(ProjectWriterError):
            ProjectWriter.write(target_dir, [_make_file(Path("file.tf"))])

    def test_absolute_output_path_raises(self, tmp_path):
        file = _make_file(Path("/etc/passwd"), "evil")
        with pytest.raises(InvalidFilePathError) as exc_info:
            ProjectWriter.write(tmp_path, [file])
        assert exc_info.value.code == InvalidFilePathCode.ABSOLUTE_PATH
        assert exc_info.value.path == Path("/etc/passwd")

    def test_path_traversal_raises(self, tmp_path):
        file = _make_file(Path("../outside.txt"), "evil")
        with pytest.raises(InvalidFilePathError) as exc_info:
            ProjectWriter.write(tmp_path, [file])
        assert exc_info.value.code == InvalidFilePathCode.PATH_TRAVERSAL
        assert exc_info.value.path == Path("../outside.txt")

    def test_nested_path_traversal_raises(self, tmp_path):
        file = _make_file(Path("subdir/../../outside.txt"), "evil")
        with pytest.raises(InvalidFilePathError) as exc_info:
            ProjectWriter.write(tmp_path, [file])
        assert exc_info.value.code == InvalidFilePathCode.PATH_TRAVERSAL

    def test_no_files_written_outside_target_dir(self, tmp_path):
        target_dir = tmp_path / "project"
        target_dir.mkdir()
        outside = tmp_path / "outside.txt"
        file = _make_file(Path("../outside.txt"), "evil")
        with pytest.raises(InvalidFilePathError):
            ProjectWriter.write(target_dir, [file])
        assert not outside.exists()
