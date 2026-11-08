"""
Tests that all SQLAlchemy models can be safely re-imported or reloaded
without raising sqlalchemy.exc.InvalidRequestError ('Table already defined').
Critical for Streamlit Cloud and hot-reload environments.
"""

import subprocess
import sys


def test_models_safe_reimport():
    """Verify that repeatedly reloading all model modules does not raise InvalidRequestError."""
    code = (
        "import importlib\n"
        "import taskvault.models\n"
        "import taskvault.models.security\n"
        "import taskvault.models.project\n"
        "import taskvault.models.tag\n"
        "import taskvault.models.task\n"
        "import taskvault.models.focus\n"
        "modules = [\n"
        "    taskvault.models.security,\n"
        "    taskvault.models.project,\n"
        "    taskvault.models.tag,\n"
        "    taskvault.models.task,\n"
        "    taskvault.models.focus,\n"
        "    taskvault.models,\n"
        "]\n"
        "for _ in range(2):\n"
        "    for mod in modules:\n"
        "        importlib.reload(mod)\n"
        "assert hasattr(taskvault.models, 'User')\n"
        "assert hasattr(taskvault.models, 'FocusSession')\n"
        "assert hasattr(taskvault.models, 'Task')\n"
        "assert hasattr(taskvault.models, 'Project')\n"
        "assert hasattr(taskvault.models, 'Tag')\n"
        "print('SAFE_REIMPORT_PASSED')\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "SAFE_REIMPORT_PASSED" in result.stdout
