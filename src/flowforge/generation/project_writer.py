from enum import StrEnum
from pathlib import Path

from .models import GeneratedFile, WriterResult


class ProjectWriterError(Exception):
    """Base exception for errors that occur during project writing."""


class MissingTargetDirectoryError(ProjectWriterError):
    """Raised when the target directory for writing does not exist."""

    def __init__(self, target_dir: Path):
        super().__init__(f"Target directory does not exist: {target_dir}")
        self.target_dir = target_dir


class InvalidFilePathCode(StrEnum):
    ABSOLUTE_PATH = "absolute_path"
    PATH_TRAVERSAL = "path_traversal"


class InvalidFilePathError(ProjectWriterError):
    """Raised when a GeneratedFile has an invalid path (e.g. absolute path)."""

    def __init__(self, path: Path, code: InvalidFilePathCode):
        msg_suffix = (
            "GeneratedFile paths must be relative."
            if code == InvalidFilePathCode.ABSOLUTE_PATH
            else "Path traversal is not allowed."
        )
        super().__init__(f"Invalid file path: {path}. {msg_suffix}")
        self.path = path
        self.code = code


class ProjectWriter:
    """Responsible for writing generated files to disk."""

    @staticmethod
    def write(target_dir: Path, files: list[GeneratedFile]) -> WriterResult:
        """Write the generated files to disk, respecting the overwrite flag.

        Args:
            target_dir: The directory where the files should be written.
            files: A list of GeneratedFile instances to write.

        Returns:
            A WriterResult containing the lists of written and skipped files, and any
            errors that occurred.
        """
        result = WriterResult()
        for file in files:
            if file.path.is_absolute():
                raise InvalidFilePathError(file.path, InvalidFilePathCode.ABSOLUTE_PATH)
            if ".." in file.path.parts:
                raise InvalidFilePathError(
                    file.path, InvalidFilePathCode.PATH_TRAVERSAL
                )
            if not target_dir.resolve().exists():
                raise MissingTargetDirectoryError(target_dir)

            outpath = target_dir.resolve() / file.path
            outpath.parent.mkdir(parents=True, exist_ok=True)
            if file.overwrite or not outpath.exists():
                try:
                    outpath.write_text(file.content, "utf-8")
                except Exception as e:
                    result.errors[str(outpath)] = e
                else:
                    result.written_files.append(file)
            else:
                result.skipped_files.append(file)
        return result
