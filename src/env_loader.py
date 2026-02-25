"""Load environment variables from a .env file."""
import os


def load_env(path=None):
    """Load key=value pairs from a .env file into os.environ.

    Skips comments (#) and blank lines. Safe if file doesn't exist.
    """
    if path is None:
        path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", ".env",
        )
    if not os.path.exists(path):
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ[key.strip()] = value.strip()
