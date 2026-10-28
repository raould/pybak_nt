* TODO: frankly the bencoding is now a little nightmare, partly because i was trying to inline it
rather than pay the overhead of marshalling just before sending. that's also due to
the limitations of bencoding and python2 vs. python3 where it is not straight-forward
to know how to unmarshall ie was is a python2 str() of bytes, or was it a python3 string
that got converted into bytes?

* TODO: add missing mypy typings in all code.

* TODO: since 'N' is passed around, make the crawl code be an actual class that takes
the 'N' at construction time.

###

Claude: Yes, it works with mypy, with one catch. For mypy to keep
checking the code twice, once with bytes names and once with text, the
class itself has to be generic in `PkOsName`. Normally that means
`class Crawler(typing.Generic[PkOsName])`, and that base list runs at
import time, where Python 2.0 has no `typing`. I tried the obvious
workarounds in a scratch file, and one of them works.

**What fails:** making the base a variable, as in `if MYPY: CrawlBase
  = typing.Generic[T]` and then `class Crawler(CrawlBase)`. mypy
  rejects it ("Variable ... is not valid as a type", "Invalid base
  class").

**What works:** a base class that is generic for mypy and does nothing at runtime.

```python
if MYPY:
    class PkGenericBase(typing.Generic[PkOsName]):
        pass
else:
    PkOsName = None
    class _PlainBase:
        pass
    class _Subscriptable:
        def __getitem__(self, key):
            return _PlainBase
    PkGenericBase = _Subscriptable()

class Crawler(PkGenericBase[PkOsName]):
    def __init__(self, N):
        # type: (pk.PkNamingP[pk.PkOsName]) -> None
        self.N = N  # type: pk.PkNamingP[pk.PkOsName]
    def crawl_dir(self, ...):
        # type: (...) -> None
        ... self.N.listdir(dir_path_list) ...
```

In the scratch test:
- mypy gave `Crawler(BytesNaming-like)` the type `Crawler[bytes]`, and every method using `PkOsName` was checked as bytes.
- Passing a `str` path was an error.
- A method that returned a name where `bytes` was required failed in the text check, so both checks were still running.
- At runtime, `Crawler`'s base is just the empty class, on Python 3. It should also hold on Python 2.0, since a class with `__getitem__` that returns a class is old-style Python, but I haven't run 2.0 here.

Some details to know:
- **`self.N` needs its own type comment.** Without it, mypy `--strict` said "Need type annotation" and treated `self.N` as `Any`. That silently turned off checking for every `self.N` call, so the comment is required.
- **The shim belongs in one shared place,** most naturally portapy as something like `ppy.PpyGenericBase1`, since it's a general workaround for Python 2.0. `pk_types` would re-export it under the type variable.
- **`main` keeps its `isinstance` dispatch.** `Crawler(N)` inside each branch gives `Crawler[bytes]` or `Crawler[str]`, the same as `run(arg, N)` does now.
- **What a class adds:** fewer arguments, and a natural home for per-run state that's currently threaded through calls (`allowed_devs`, `header`, perhaps the sender).
- **What it costs:** helpers that are pure functions of `N` today (`classify_entry`, `smells.*`, `client_util.to_hex_path_list`) would either become methods or keep taking `self.N`. If only the crawl becomes a class, the other modules still receive `N` explicitly, and that's fine.
