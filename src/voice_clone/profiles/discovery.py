import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class VoiceProfile:
    name: str
    model_path: Path
    index_path: Path | None


def discover_profiles(voices_dir: Path) -> list[VoiceProfile]:
    if not voices_dir.is_dir():
        return []
    folders = sorted((p for p in voices_dir.iterdir() if p.is_dir()), key=lambda p: p.name)
    profiles = (_build_profile(folder) for folder in folders)
    return [profile for profile in profiles if profile is not None]


def _build_profile(folder: Path) -> VoiceProfile | None:
    models = sorted(folder.glob("*.pth"), key=lambda p: p.name)
    if not models:
        return None
    if len(models) > 1:
        logger.warning(
            "Profile %s has %d .pth files, using %s", folder.name, len(models), models[0].name
        )
    indexes = sorted(folder.glob("*.index"), key=lambda p: p.name)
    return VoiceProfile(
        name=folder.name,
        model_path=models[0],
        index_path=indexes[0] if indexes else None,
    )
