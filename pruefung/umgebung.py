"""
PadelCircle.py ausserhalb von Streamlit lauffähig machen.

Die App ist eine einzige Datei und läuft normalerweise in Streamlit
Cloud mit Zugang zu Google Sheets. Zum Prüfen braucht es beides nicht:
hier werden Streamlit, gspread und die übrigen Aussenanschlüsse durch
Attrappen ersetzt. Die Rechenlogik selbst läuft unverändert.

    import umgebung          # muss VOR PadelCircle importiert werden
    import PadelCircle as PC
"""
import sys, types, functools, importlib.abc, importlib.machinery, os

MELDUNGEN = []


def _attrappe(name):
    modul = types.ModuleType(name)

    class Alles:
        def __init__(s, *a, **k): pass
        def __call__(s, *a, **k): return Alles()
        def __getattr__(s, n): return Alles()
        def __enter__(s): return s
        def __exit__(s, *a): return False
        def __bool__(s): return False
        def __iter__(s): return iter([])

    modul.__getattr__ = lambda n: Alles()
    return modul, Alles


st, Alles = _attrappe("streamlit")
st.error = lambda m, *a, **k: MELDUNGEN.append(("fehler", str(m)))
st.warning = lambda m, *a, **k: MELDUNGEN.append(("warnung", str(m)))


def _cache(*da, **dk):
    """@st.cache_data mit echtem Gedächtnis und .clear()."""
    def deko(fn):
        speicher = {}

        @functools.wraps(fn)
        def huelle(*a, **k):
            schluessel = (a, tuple(sorted(k.items())))
            if schluessel not in speicher:
                speicher[schluessel] = fn(*a, **k)
            return speicher[schluessel]

        huelle.clear = lambda *a, **k: speicher.clear()
        return huelle
    return deko(da[0]) if len(da) == 1 and callable(da[0]) and not dk else deko


st.cache_data = st.cache_resource = _cache


class _Zustand(dict):
    """st.session_state — als Schlüssel UND als Attribut ansprechbar."""
    def __getattr__(s, n):
        try:
            return s[n]
        except KeyError:
            raise AttributeError(n)

    def __setattr__(s, n, v): s[n] = v
    def __delattr__(s, n): s.pop(n, None)


st.session_state = _Zustand()
st.secrets = {}
for n in ("write", "markdown", "info", "success", "progress", "empty",
          "columns", "container", "set_page_config", "stop", "rerun",
          "caption", "toast", "expander", "dataframe", "button"):
    setattr(st, n, Alles())
sys.modules["streamlit"] = st

_AUSSEN = ("gspread", "plotly", "google", "streamlit.components",
           "streamlit_javascript")


class _Finder(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    def find_spec(s, n, path=None, target=None):
        if any(n == p or n.startswith(p + ".") for p in _AUSSEN):
            return importlib.machinery.ModuleSpec(n, s)

    def create_module(s, spec): return _attrappe(spec.name)[0]
    def exec_module(s, m): pass


sys.meta_path.insert(0, _Finder())
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
