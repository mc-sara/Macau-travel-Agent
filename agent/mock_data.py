import json
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd


def project_root() -> Path:
    """Return the demo project root directory."""
    return Path(__file__).resolve().parents[1]


def data_path(filename: str) -> Path:
    """Return an absolute path under the project's data directory."""
    return project_root() / "data" / filename


def load_merchants() -> Dict[str, List[Dict[str, Any]]]:
    """Load mock merchant/activity data from JSON."""
    path = data_path("mock_merchants.json")
    return json.loads(path.read_text(encoding="utf-8"))


def load_excel_preview(filename: str, max_rows: int = 5) -> List[Dict[str, Any]]:
    """Read a small preview from an Excel file as records for UI/debug display."""
    path = data_path(filename)
    if not path.exists():
        raise FileNotFoundError(path)
    df = pd.read_excel(path, nrows=max_rows)
    return df.fillna("").to_dict(orient="records")
