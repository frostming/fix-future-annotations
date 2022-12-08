from pathlib import Path
import shutil
import pytest

from fix_future_annotations._main import fix_file
from fix_future_annotations._config import Config

SAMPLES = Path(__file__).with_name("samples")


def _load_samples() -> list:
    samples = []
    for fixed in SAMPLES.glob("*_fix.py"):
        origin = SAMPLES / fixed.name.replace("_fix", "")
        if origin.exists():
            samples.append(pytest.param(origin, fixed, id=origin.stem))
    return samples


@pytest.mark.parametrize("origin, fixed", _load_samples())
def test_fix_samples(origin: Path, fixed: Path, tmp_path: Path) -> None:
    copied = shutil.copy2(origin, tmp_path)
    config = Config(exclude_lines=["# ffa: ignore", "class NoFix:"])
    result = fix_file(copied, write=True, config=config)

    assert fixed.read_text() == Path(copied).read_text()

    result = fix_file(copied, write=False, config=config)
    assert not result
