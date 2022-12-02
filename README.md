# fix-future-annotations

A CLI and pre-commit hook to upgrade the typing annotations syntax to PEP 585 and PEP 604.


## Upgrade Details

### [PEP 585] – Type Hinting Generics In Standard Collections

<table>
<thead>
<tr><th>Old</th><th>New</th></tr>
</thead>
<tbody>
<tr><td>

```python
typing.Dict[str, int]
List[str]
```
</td><td>

```python
dict[str, int]
list[str]
```
</td></tr></tbody>
</table>


### [PEP 604] – Allow writing union types as `X | Y`

<table>
<thead>
<tr><th>Old</th><th>New</th></tr>
</thead>
<tbody>
<tr><td>

```python
typing.Union[str, int]
Optional[str]
```
</td><td>

```python
str | int
str | None
```
</td></tr></tbody>
</table>

### [PEP 563] – Postponed Evaluation of Annotations

<table>
<thead>
<tr><th>Old</th><th>New</th></tr>
</thead>
<tbody>
<tr><td>

```python
def create() -> "Foo": pass
```
</td><td>

```python
def create() -> Foo: pass
```
</td></tr></tbody>
</table>

### Import aliases handling

<table>
<thead>
<tr><th>Old</th><th>New</th></tr>
</thead>
<tbody>
<tr><td>

```python
import typing as t
from typing import Tuple as MyTuple

def foo() -> MyTuple[str, t.Optional[int]]:
    pass
```
</td><td>

```python
from __future__ import annotations

import typing as t

def foo() -> tuple[str, int | None]:
    pass
```
</td></tr></tbody>
</table>

### Full example

<table>
<thead>
<tr><th>Old</th><th>New</th></tr>
</thead>
<tbody>
<tr><td>

```python
from typing import Union, Dict, Optional, Tuple

# non-annotation usage will be preserved
MyType = Union[str, int]


def foo() -> Tuple[Dict[str, int], Optional[str]]:
    ...
```
</td><td>

```python
from __future__ import annotations

from typing import Union

# non-annotation usage will be preserved
MyType = Union[str, int]


def foo() -> tuple[dict[str, int], str | None]:
    ...
```
</td></tr></tbody>
</table>

Unused import names will be removed, and if `from __future__ import annotations` is not found in the script, it will be automatically added if the new syntax is being used.

## Use as pre-commit hook

Add the following to your `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/frostming/fix-future-annotations
    rev: x.y.z  # a released version tag
    hooks:
      - id: fix-future-annotations
```

## Use as command line tool

```bash
python3 -m pip install git+https://github.com/frostming/fix-future-annotations.git

fix-future-annotations my_script.py
```

## License

This work is distributed under [MIT](https://github.com/frostming/fix-future-annotations/blob/main/README.md) license.

[PEP 563]: https://peps.python.org/pep-0563/
[PEP 585]: https://peps.python.org/pep-0585/
[PEP 604]: https://peps.python.org/pep-0604/
