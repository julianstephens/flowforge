from pathlib import Path

from flowforge.generation.models import GeneratedFile, WriterResult
from flowforge.generation.project_writer import ProjectWriter


def _make_file(
    path: Path, content: str = "content", overwrite: bool = False
) -> GeneratedFile:
    return GeneratedFile(path=path, content=content, overwrite=overwrite)


class TestProjectWriter:
    def test_returns_writer_result(self, tmp_path):
        result = ProjectWriter.write([_make_file(tmp_path / "file.tf")])
        assert isinstance(result, WriterResult)

    def test_writes_file_content(self, tmp_path):
        target = tmp_path / "out" / "main.tf"
        ProjectWriter.write([_make_file(target, "hello world")])
        assert target.read_text() == "hello world"

    def test_creates_parent_directories(self, tmp_path):
        target = tmp_path / "a" / "b" / "c" / "file.tf"
        ProjectWriter.write([_make_file(target)])
        assert target.exists()

    def test_written_file_appears_in_written_files(self, tmp_path):
        target = tmp_path / "file.tf"
        file = _make_file(target)
        result = ProjectWriter.write([file])
        assert file in result.written_files
        assert result.skipped_files == []
        assert result.errors == {}

    def test_writes_multiple_files(self, tmp_path):
        files = [
            _make_file(tmp_path / "a.tf", "aaa"),
            _make_file(tmp_path / "b.tf", "bbb"),
        ]
        result = ProjectWriter.write(files)
        assert (tmp_path / "a.tf").read_text() == "aaa"
        assert (tmp_path / "b.tf").read_text() == "bbb"
        assert len(result.written_files) == 2

    def test_empty_list_returns_empty_result(self):
        result = ProjectWriter.write([])
        assert result.written_files == []
        assert result.skipped_files == []
        assert result.errors == {}

    def test_existing_file_skipped_when_overwrite_false(self, tmp_path):
        target = tmp_path / "file.tf"
        target.write_text("original")
        file = _make_file(target, "new content", overwrite=False)
        result = ProjectWriter.write([file])
        assert file in result.skipped_files
        assert result.written_files == []
        assert target.read_text() == "original"

    def test_existing_file_overwritten_when_overwrite_true(self, tmp_path):
        target = tmp_path / "file.tf"
        target.write_text("original")
        file = _make_file(target, "updated", overwrite=True)
        result = ProjectWriter.write([file])
        assert file in result.written_files
        assert result.skipped_files == []
        assert target.read_text() == "updated"

    def test_new_file_written_regardless_of_overwrite_flag(self, tmp_path):
        target = tmp_path / "new.tf"
        file = _make_file(target, "fresh", overwrite=False)
        result = ProjectWriter.write([file])
        assert target.read_text() == "fresh"
        assert file in result.written_files

    def test_processing_continues_after_skip(self, tmp_path):
        existing = tmp_path / "exists.tf"
        existing.write_text("old")
        new_target = tmp_path / "new.tf"
        skipped = _make_file(existing, "conflict", overwrite=False)
        written = _make_file(new_target, "ok")
        result = ProjectWriter.write([skipped, written])
        assert skipped in result.skipped_files
        assert written in result.written_files
        assert new_target.read_text() == "ok"

    def test_write_error_collected_not_raised(self, tmp_path):
        target = tmp_path / "file.tf"
        file = _make_file(target, "content")
        original_write_text = Path.write_text

        def raise_on_write(_self, *_args, **_kwargs):
            raise OSError("disk full")

        Path.write_text = raise_on_write
        try:
            result = ProjectWriter.write([file])
        finally:
            Path.write_text = original_write_text

        assert str(target) in result.errors
        assert isinstance(result.errors[str(target)], OSError)
        assert result.written_files == []

    def test_processing_continues_after_write_error(self, tmp_path):
        first = tmp_path / "first.tf"
        second = tmp_path / "second.tf"
        files = [_make_file(first, "a"), _make_file(second, "b")]

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
            result = ProjectWriter.write(files)
        finally:
            Path.write_text = original_write_text

        assert str(first) in result.errors
        assert files[1] in result.written_files
        assert second.read_text() == "b"
