from pathlib import Path
import shutil
import pytest

from fix_future_annotations._main import fix_file

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
    result = fix_file(copied, True)

    assert fixed.read_text() == Path(copied).read_text()

    result = fix_file(copied, False)
    assert not result
