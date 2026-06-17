"""FreePDF Suite — Qt6 (PySide6) UI shell.

Wave-2 frontend slice. Provides the application window, the module-driven menu,
and a basic page viewer. Business logic lives in core/ and the modules; this
package only renders and dispatches per the intent-contract (Section 6).
"""

from __future__ import annotations

__version__ = "0.1.0"

from .app import main, run

__all__ = ["main", "run", "__version__"]
