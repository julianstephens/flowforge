from .models import GeneratedFile, WriterResult


class ProjectWriter:
    """Responsible for writing generated files to disk."""

    @staticmethod
    def write(files: list[GeneratedFile]) -> WriterResult:
        """Write the generated files to disk, respecting the overwrite flag.

        Args:
            files: A list of GeneratedFile instances to write.

        Returns:
            A WriterResult containing the lists of written and skipped files, and any
            errors that occurred.
        """
        result = WriterResult()
        for file in files:
            if file.overwrite or not file.path.exists():
                file.path.parent.mkdir(parents=True, exist_ok=True)
                try:
                    file.path.write_text(file.content, "utf-8")
                except Exception as e:
                    result.errors[str(file.path)] = e
                else:
                    result.written_files.append(file)
            else:
                result.skipped_files.append(file)
        return result
