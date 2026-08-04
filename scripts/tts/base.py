"""Giao diện chung, không cho phép nhà cung cấp tự chuyển dự phòng."""

from abc import ABC, abstractmethod
from pathlib import Path


class TtsProvider(ABC):
    ten_nha_cung_cap: str

    @abstractmethod
    async def synthesize(self, text: str, destination: Path, preset) -> str:
        """Tạo MP3 và trả về Voice ID thực tế."""
