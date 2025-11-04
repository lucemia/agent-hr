"""
Factory for creating resume importers.
"""

from .interface import ResumeImporter


class ImporterFactory:
    """Factory class for creating resume importers"""

    _importers: dict[str, type[ResumeImporter]] = {}

    @classmethod
    def register(cls, source_name: str, importer_class: type[ResumeImporter]):
        """Register an importer class for a source"""
        cls._importers[source_name.lower()] = importer_class

    @classmethod
    def create(cls, source_name: str) -> ResumeImporter:
        """Create an importer instance for the given source"""
        source_key = source_name.lower()

        if source_key not in cls._importers:
            available = ", ".join(cls._importers.keys())
            raise ValueError(
                f"Unknown source '{source_name}'. Available sources: {available}"
            )

        importer_class = cls._importers[source_key]
        return importer_class()

    @classmethod
    def get_available_sources(cls) -> list[str]:
        """Get list of available source names"""
        return list(cls._importers.keys())
