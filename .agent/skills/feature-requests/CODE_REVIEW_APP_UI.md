# Senior Code Review: app_ui.py

**Reviewer**: Claude Code  
**Date**: 2026-04-06  
**Status**: Actionable findings with refactoring plan included

---

## Executive Summary

The UI demonstrates good intentions with Terra design system theming and solid Streamlit patterns, but suffers from **monolithic structure**, **CSS smell**, **tight coupling** between concerns, and **poor separation of responsibilities**. The codebase would benefit significantly from modularization and extraction of business logic.

**Key Issues**: 
- ~1,300 lines in single file (unmaintainable)
- Embedded CSS bloat + inline style logic
- No abstraction layer for state management
- Tight coupling to backend imports
- Repetitive conditional rendering for deployed vs. local modes

---

## Architecture & Structure Issues

### 1. **Monolithic File Structure** ⚠️ CRITICAL

**Issue**: The entire UI is 1,300+ lines in a single file, mixing:
- CSS theming (250+ lines)
- Progress tracking logic (`ProgressTracker`, `QueueLogHandler`)
- Session state management
- File picker helpers with subprocess calls
- Main UI rendering
- Background thread orchestration
- Result display

**Impact**: 
- Extremely difficult to test
- Impossible to reuse components
- Cognitive load is massive
- Navigation within file requires constant scrolling

**Refactoring Strategy**:
```
app_ui.py (entry point, ~100 lines)
├── ui/
│   ├── __init__.py
│   ├── theme.py          (CSS + design tokens)
│   ├── components.py     (reusable UI blocks)
│   ├── sidebar.py        (settings panel)
│   ├── inputs.py         (audio/video/output sections)
│   └── results.py        (output display)
├── state/
│   ├── __init__.py
│   └── session.py        (session state management)
├── workers/
│   ├── __init__.py
│   ├── progress.py       (ProgressTracker)
│   └── runner.py         (background thread logic)
├── io/
│   ├── __init__.py
│   └── file_picker.py    (native file dialogs)
└── adapters/
    ├── __init__.py
    └── backend.py        (engine imports, isolated)
```

---

## Code Quality Issues

### 2. **CSS as a String Constant** ⚠️ MAJOR

**Lines 37-398**: 360+ lines of CSS embedded in a single `st.markdown()` call.

**Problems**:
- ❌ No syntax highlighting in editor
- ❌ Unmaintainable — changes require scrolling through massive string
- ❌ Design tokens hardcoded as hex values (no single source of truth)
- ❌ Difficult to version control diffs
- ❌ Impossible to test or lint

**Evidence**:
```python
st.markdown("""
<style>
    :root {
        --primary: #4a7c59;
        --bg-cream: #faf6f0;
        ...
    }
    /* 350+ more lines */
</style>
""", unsafe_allow_html=True)  # <-- unsafe_allow_html flag glossed over
```

**Solution**: Extract to `ui/theme.py`:
```python
# ui/theme.py
DESIGN_TOKENS = {
    "primary": "#4a7c59",
    "bg_cream": "#faf6f0",
    # ...
}

THEME_CSS = f"""
<style>
    :root {{
        --primary: {DESIGN_TOKENS['primary']};
        ...
    }}
</style>
"""

def apply_theme():
    st.markdown(THEME_CSS, unsafe_allow_html=True)
```

---

### 3. **Global Initialization at Module Level** ⚠️ MAJOR

**Lines 26-30, 562**: Page config and state init called at import time:

```python
st.set_page_config(...)  # Line 26
st.markdown(THEME_CSS)   # Line 37
_init_state()            # Line 562
```

**Problems**:
- ❌ Executed on every Streamlit rerun (inefficient)
- ❌ Can't be tested in isolation
- ❌ Forces all initialization even for partial runs
- ❌ Violates Python import-time behavior expectations

**Best Practice**: Page config MUST be first call (correct), but everything else should be lazy or guarded:

```python
# Correct pattern
st.set_page_config(...)  # Must be first

if "initialized" not in st.session_state:
    _init_state()
    st.session_state["initialized"] = True
```

---

### 4. **Subprocess-Based File Dialogs** ⚠️ MEDIUM

**Lines 600-672**: Using `subprocess.run()` to spawn Python scripts with tkinter:

```python
def _run_safe_tk_dialog(script: str) -> str | None:
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        check=False,
    )
```

**Concerns**:
- ⚠️ **Security**: String interpolation in script (lines 628) — potential injection risk
- ⚠️ **Fragility**: Depends on tkinter availability + subprocess overhead
- ⚠️ **UX**: Spawns visible windows; poor feedback
- ⚠️ **Maintenance**: Hard to debug cross-process errors

**Evidence of Risk**:
```python
script = f"""
import tkinter as tk
path = filedialog.askdirectory(title='{title}')  # <-- title is interpolated!
```

If a user passes `title="'; import os; os.system(...); '"`, this could execute arbitrary code.

**Solutions**:
1. **For Streamlit Cloud**: Disable entirely + show message
2. **For Local**: Use safer APIs or accept file input only
3. **Refactor**: Move to separate module with proper validation

---

### 5. **Implicit Dependencies on Environment** ⚠️ MEDIUM

**Lines 569-583**: Lazy imports with decorators:

```python
@st.cache_resource(show_spinner="Loading engine…")
def _load_engine():
    from src.core.app import BachataSyncEngine
    return BachataSyncEngine()
```

**Issues**:
- ❌ Silent failures if backend isn't installed
- ❌ No version checking
- ❌ Cached at module level — hard to invalidate for tests
- ❌ ImportError on first call to UI → poor UX

**Better Approach**:
```python
def get_engine():
    """Lazy-load engine with explicit error handling."""
    try:
        from src.core.app import BachataSyncEngine
        return BachataSyncEngine()
    except ImportError as e:
        st.error(f"Backend not available: {e}")
        st.stop()
```

---

### 6. **Tight Coupling to PacingConfig** ⚠️ MEDIUM

**Lines 1177-1216**: Direct mapping of UI inputs to `PacingConfig` fields:

```python
if speed_ramp_organic:
    pacing_kwargs["speed_ramp_organic"] = True
    pacing_kwargs["speed_ramp_sensitivity"] = speed_ramp_sensitivity
    ...
# Repeat 8+ times for different effects
```

**Problems**:
- ❌ If backend changes `PacingConfig`, UI breaks silently
- ❌ No validation at UI layer (validation happens in backend)
- ❌ Magic string keys — no IDE autocomplete
- ❌ Duplication between UI and backend definitions

**Solution**: Create UI model layer:
```python
# adapters/backend.py
@dataclass
class UISettings:
    """UI layer representation of pacing options."""
    genre: str | None = None
    speed_ramp_organic: bool = False
    speed_ramp_sensitivity: float = 1.0
    # ...
    
    def to_pacing_config(self) -> PacingConfig:
        """Convert to backend model with validation."""
        # Validate here, raise early if invalid
        return PacingConfig(**self.to_dict())
```

---

### 7. **Session State Management is Implicit** ⚠️ MAJOR

**Lines 543-562**: State initialized via dict, accessed via string keys throughout:

```python
def _init_state() -> None:
    defaults = {
        "running": False,
        "log_lines": [],
        "result_path": None,
        ...
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

# Later, accessed as:
st.session_state["running"]  # Magic string!
```

**Issues**:
- ❌ No type hints — string keys don't autocomplete
- ❌ Easy to typo (`"running"` vs `"runnning"`)
- ❌ No single source of truth for available state keys
- ❌ Tests can't verify state shape

**Better Pattern**:
```python
# state/session.py
class SessionState:
    """Typed wrapper around st.session_state."""
    
    @property
    def is_running(self) -> bool:
        return st.session_state.get("running", False)
    
    @is_running.setter
    def is_running(self, value: bool) -> None:
        st.session_state["running"] = value
    
    @property
    def log_lines(self) -> list[str]:
        return st.session_state.get("log_lines", [])

# Usage:
state = SessionState()
state.is_running = True  # Typed, autocomplete works
```

---

### 8. **Complex Conditional Rendering for Deployment Modes** ⚠️ MEDIUM

**Lines 829-945**: Repeated if/else for "deployed vs. local" UI:

```python
if is_deployed:
    # Upload-only UI
    uploaded_audio = st.file_uploader(...)
else:
    # Upload + path picker UI
    col_audio_upload, col_audio_path = st.columns(...)
    uploaded_audio = st.file_uploader(...)
    # More code...
    
# Repeat for video, b-roll, output...
```

**Issues**:
- ❌ Duplication across 3+ sections (audio, video, output)
- ❌ Easy to forget to update one branch → inconsistent UI
- ❌ Hard to test both code paths
- ❌ Increases cognitive load

**Solution**: Extract to component functions:
```python
def render_audio_input(mode: Literal["local", "deployed"]) -> AudioInput:
    """Single source of truth for audio input UI."""
    if mode == "deployed":
        return AudioInput(uploaded=st.file_uploader(...))
    else:
        return AudioInput(
            uploaded=st.file_uploader(...),
            path=st.text_input(...)
        )
```

---

### 9. **Error Handling is Minimal** ⚠️ MEDIUM

**Lines 1113-1121**: Background thread catches all exceptions with `except Exception`:

```python
except Exception:  # noqa: BLE001
    error_details = tb_module.format_exc()
    log_queue.put(f"__ERROR__{error_details}")
```

**Issues**:
- ⚠️ Catches `SystemExit`, `KeyboardInterrupt` — can hide real issues
- ⚠️ Error message is raw traceback — not user-friendly
- ⚠️ No logging level distinction (ERROR vs. CRITICAL)
- ⚠️ No recovery mechanism

**Better Pattern**:
```python
try:
    # ...
except KeyboardInterrupt:
    log_queue.put("__CANCELLED__")
except (FileNotFoundError, ValueError) as e:
    # Expected errors, user-friendly message
    log_queue.put(f"__USER_ERROR__{str(e)}")
except Exception as e:
    # Unexpected errors, log full trace
    log_queue.put(f"__ERROR__{traceback.format_exc()}")
```

---

### 10. **Magic String Protocols for Inter-Component Communication** ⚠️ MAJOR

**Lines 1290-1300**: Parsing log messages with magic strings:

```python
if line.startswith("__DONE__"):
    done = True
elif line.startswith("__RESULT__"):
    st.session_state["result_path"] = line[len("__RESULT__"):]
elif line.startswith("__ERROR__"):
    st.session_state["error"] = line[len("__ERROR__"):]
```

**Problems**:
- ❌ Fragile protocol — easy to break
- ❌ No schema validation
- ❌ Hard to debug (log message format changed? Silent failure)
- ❌ Impossible to test without running full pipeline

**Solution**: Use dataclass + JSON:
```python
from dataclasses import asdict
from enum import Enum

class MessageType(Enum):
    DONE = "done"
    RESULT = "result"
    ERROR = "error"

@dataclass
class WorkerMessage:
    type: MessageType
    payload: str = ""
    
    def to_json(self) -> str:
        return json.dumps({
            "type": self.type.value,
            "payload": self.payload
        })
    
    @classmethod
    def from_json(cls, s: str):
        data = json.loads(s)
        return cls(MessageType(data["type"]), data["payload"])
```

---

## Best Practices Violations

### 11. **No Tests** ⚠️ CRITICAL

- Zero unit tests for UI logic
- No component tests
- No integration tests
- `ProgressTracker` logic is untestable (hardcoded heuristics)
- File picker functions can't be tested

**Impact**: Refactoring is terrifying; bugs slip in silently.

---

### 12. **No Type Hints in Key Functions** ⚠️ MAJOR

**Examples**:
```python
def _run_generation(  # Has type hints ✓
    audio_resolved: str,
    video_dir_path: str,
    ...
) -> None:

# But these don't:
def _pick_folder(title: str = "Select folder") -> str | None:
    script = f"""..."""  # `script` is untyped
    return _run_safe_tk_dialog(script)  # Return type ok, but intermediate is not

# And this:
pacing_kwargs: dict  # <-- Should be dict[str, Any] or TypedDict
```

**Fix**: Consistent type hints everywhere:
```python
from typing import TypedDict

class PacingOptionsDict(TypedDict, total=False):
    genre: str
    speed_ramp_organic: bool
    # ... all keys

pacing_kwargs: PacingOptionsDict = {}
```

---

### 13. **Bare `except` with `# noqa: BLE001`** ⚠️ MEDIUM

**Lines 522, 615, 1113**: Suppressing linter warnings instead of fixing:

```python
except Exception:  # noqa: BLE001
    pass
```

This tells the linter "I know this is bad, shut up" — not addressing the root issue.

**Fix**: Catch specific exceptions:
```python
except (OSError, ValueError, KeyError) as e:
    logger.error(f"Failed: {e}")
```

---

### 14. **Magic Numbers in ProgressTracker** ⚠️ MEDIUM

**Lines 420-427**:
```python
STAGE_HEURISTICS = {
    "Analysing audio": 10,
    "Scanning video": 10,
    # ...
    "Rendering montage": 65,  # <-- Where does 65% come from?
}
```

- ❌ No explanation of how these were derived
- ❌ Will become outdated as pipeline changes
- ❌ No way to update them without editing code

**Better**: Load from config:
```python
# montage_config.yaml
pipeline:
  stage_heuristics:
    rendering: 65
    audio_analysis: 10

# In app_ui.py:
def load_stage_heuristics() -> dict[str, int]:
    config = load_yaml("montage_config.yaml")
    return config["pipeline"]["stage_heuristics"]
```

---

### 15. **Mutable Default Arguments** ⚠️ MINOR

Not present in this file, but watch for it in refactored code.

---

## Performance Issues

### 16. **Inefficient Log Queue Draining** ⚠️ MEDIUM

**Lines 1284-1300**: Drains entire queue on every rerun:

```python
while True:
    try:
        line = log_queue.get_nowait()
    except queue.Empty:
        break
    # Process line...
    st.session_state["log_lines"].append(line)  # Rebuilds full list
```

**Issues**:
- ⚠️ As log_lines grows (1000+ items), appending becomes slow
- ⚠️ Session state balloons (memory leak risk)
- ⚠️ `st.code()` renders entire log every rerun

**Solution**: Maintain index + render window:
```python
class LogBuffer:
    def __init__(self, max_lines: int = 1000):
        self.lines = collections.deque(maxlen=max_lines)
        self.last_index = 0
    
    def append(self, line: str):
        self.lines.append(line)
    
    def get_new(self) -> list[str]:
        """Return only new lines since last call."""
        new = list(self.lines)[self.last_index:]
        self.last_index = len(self.lines)
        return new
```

---

### 17. **Sleeps in Hot Loop** ⚠️ MEDIUM

**Lines 1343-1344**:
```python
time.sleep(0.1)
st.rerun()  # <-- Triggers expensive page re-render
```

Every 2 seconds + 0.1s, the entire page reruns. This re-evaluates:
- All CSS (line 37)
- All sidebar inputs
- All input fields
- Theme setup

**Better**: Use Streamlit's `@st.experimental_fragment` to update only the status area.

---

## Maintainability Concerns

### 18. **No Constants/Config** ⚠️ MEDIUM

Hardcoded values scattered throughout:
```python
tempfile.NamedTemporaryFile(delete=False, suffix=suffix)  # Line 1137
tempfile.mkdtemp(prefix="bachata_videos_")  # Line 1155
"   → "  # Arrow prefix inconsistent
st.session_state["log_lines"].append(line)  # Key name repeated
```

**Solution**: Create constants module:
```python
# config.py
TEMP_VIDEO_PREFIX = "bachata_videos_"
TEMP_AUDIO_SUFFIX = ".wav"
LOG_LINE_PREFIX = "   → "
SESSION_KEY_RUNNING = "running"
MAX_LOG_LINES = 5000
```

---

## Positive Aspects ✅

1. **Good design system thinking** — Color tokens, consistent typography
2. **Graceful degradation** — Local vs. deployed modes
3. **Progress tracking** — Elapsed time, ETA estimation
4. **Lazy imports** — Avoids slow startup
5. **Threading** — Doesn't block UI
6. **Test mode flag** — Good for iteration

---

## Recommended Refactoring Plan

### Phase 1: Extract (Low Risk)
1. **Extract theme → `ui/theme.py`** (5 min)
   - Move CSS + design tokens
   - Create `apply_theme()` function
   
2. **Extract file pickers → `io/file_picker.py`** (10 min)
   - Wrap subprocess calls
   - Add security validation
   - Tests: Mock subprocess

3. **Extract progress tracking → `workers/progress.py`** (10 min)
   - Move `ProgressTracker`, `QueueLogHandler`, `QueueProgressObserver`
   - No logic change, just organization

### Phase 2: Refactor (Medium Risk)
4. **Create session state wrapper → `state/session.py`** (20 min)
   - Typed properties for all keys
   - Validation on set
   - Tests: Direct assertions

5. **Extract backend adapter → `adapters/backend.py`** (15 min)
   - Lazy imports + error handling
   - `UISettings` model
   - Tests: Mock imports

6. **Create component functions → `ui/inputs.py`** (30 min)
   - `render_audio_input(mode)`
   - `render_video_input(mode)`
   - `render_output_input(mode)`
   - Tests: Component rendering

### Phase 3: Redesign (Higher Risk)
7. **Replace magic string protocol → Message dataclasses** (30 min)
   - JSON-based communication
   - Tests: Message serialization

8. **Refactor background thread** (45 min)
   - Move to `workers/runner.py`
   - Dependency injection for engine
   - Testable with mock engine

9. **Split main app → `app_ui.py` (refactored)** (20 min)
   - Import from submodules
   - Route main page layout
   - ~100 lines only

### Testing (Ongoing)
- Add unit tests for `ProgressTracker`, `SessionState`
- Add snapshot tests for component rendering
- Add integration tests for file picker (mock subprocess)

---

## Summary Table

| Issue | Severity | Effort | Priority |
|-------|----------|--------|----------|
| Monolithic structure | CRITICAL | 3 days | 1 |
| CSS bloat | MAJOR | 1 hour | 2 |
| Session state strings | MAJOR | 2 hours | 3 |
| Magic string protocol | MAJOR | 4 hours | 4 |
| Tight backend coupling | MEDIUM | 2 hours | 5 |
| No tests | CRITICAL | 2 days | 6 |
| Conditional rendering duplication | MEDIUM | 2 hours | 7 |
| Subprocess security | MEDIUM | 1.5 hours | 8 |
| Type hints gaps | MEDIUM | 1 hour | 9 |
| Performance (log rendering) | MEDIUM | 1 hour | 10 |

---

## Quick Wins (Start Here)

1. **Move CSS to separate file** (5 min) → Immediate readability gain
2. **Add type hints to UI functions** (30 min) → Prevent bugs
3. **Create session state wrapper** (2 hours) → Eliminate string key bugs
4. **Extract file pickers** (1 hour) → Better security + testability
5. **Add docstrings** (1 hour) → Next developer understanding

---

## Questions for Product Team

1. **Deployment roadmap**: Is Streamlit Cloud deployment in scope? (Affects file picker complexity)
2. **ETA accuracy**: Are 65% / 10% heuristics validated, or estimates? (Affects confidence in tracker)
3. **Speed ramping**: Is FEAT-036 stable? (Affects refactoring scope of pacing_kwargs)
4. **Future UI**: Are you planning multiple entry points (web, desktop)? (Affects architecture choice)

