from flowforge.generation.models import GeneratedFile


class FileAlreadyExistsError(FileExistsError):
    def __init__(self, path: str):
        super().__init__(f"File already exists: {path}")
        self.path = path


class ProjectWriter:
    """Responsible for writing generated files to disk."""

    def write(self, files: list[GeneratedFile]):
        """Write the generated files to disk, respecting the overwrite flag.

        Args:
            files: A list of GeneratedFile instances to write.

        Raises:
            FileAlreadyExistsError: If a file already exists and overwrite is False.
        """
        for file in files:
            if file.overwrite or not file.path.exists():
                file.path.parent.mkdir(parents=True, exist_ok=True)
                file.path.write_text(file.content)
            else:
                raise FileAlreadyExistsError(str(file.path))
