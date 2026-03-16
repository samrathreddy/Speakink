"""Provider registry with auto-discovery."""

from __future__ import annotations

import importlib
import inspect
import logging
import pkgutil
from typing import Type

from speakink.providers.stt.base import STTProvider
from speakink.providers.llm.base import CorrectionProvider
from speakink.providers.insertion.base import InsertionMethod

logger = logging.getLogger(__name__)


class ProviderRegistry:
    """Auto-discovers and registers all providers."""

    def __init__(self):
        self._stt_providers: dict[str, Type[STTProvider]] = {}
        self._correction_providers: dict[str, Type[CorrectionProvider]] = {}
        self._insertion_methods: dict[str, Type[InsertionMethod]] = {}
        self._discover()

    def _discover(self) -> None:
        self._discover_package("speakink.providers.stt", STTProvider, self._stt_providers)
        self._discover_package("speakink.providers.llm", CorrectionProvider, self._correction_providers)
        self._discover_package("speakink.providers.insertion", InsertionMethod, self._insertion_methods)
        logger.info(
            "Discovered providers — STT: %s, Correction: %s, Insertion: %s",
            list(self._stt_providers.keys()),
            list(self._correction_providers.keys()),
            list(self._insertion_methods.keys()),
        )

    def _discover_package(self, package_name: str, base_class: type, registry: dict) -> None:
        try:
            package = importlib.import_module(package_name)
        except ImportError:
            logger.warning("Could not import package: %s", package_name)
            return

        package_path = getattr(package, "__path__", None)
        if package_path is None:
            return

        for _, module_name, _ in pkgutil.iter_modules(package_path):
            if module_name == "base":
                continue
            try:
                module = importlib.import_module(f"{package_name}.{module_name}")
                for _, cls in inspect.getmembers(module, inspect.isclass):
                    if issubclass(cls, base_class) and cls is not base_class and cls.name:
                        registry[cls.name] = cls
            except Exception:
                logger.exception("Failed to load module: %s.%s", package_name, module_name)

    def get_stt_provider(self, name: str, **kwargs) -> STTProvider:
        cls = self._stt_providers[name]
        return cls(**kwargs)

    def get_correction_provider(self, name: str, **kwargs) -> CorrectionProvider:
        cls = self._correction_providers[name]
        return cls(**kwargs)

    def get_insertion_method(self, name: str, **kwargs) -> InsertionMethod:
        cls = self._insertion_methods[name]
        return cls(**kwargs)

    @property
    def stt_providers(self) -> dict[str, Type[STTProvider]]:
        return dict(self._stt_providers)

    @property
    def correction_providers(self) -> dict[str, Type[CorrectionProvider]]:
        return dict(self._correction_providers)

    @property
    def insertion_methods(self) -> dict[str, Type[InsertionMethod]]:
        return dict(self._insertion_methods)
