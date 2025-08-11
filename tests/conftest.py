"""Test configuration and fixtures."""
from pathlib import Path

import pytest


@pytest.fixture
def project_root():
    """Return the project root directory."""
    return Path(__file__).parent.parent

@pytest.fixture
def sample_data_dir(project_root):
    """Return the sample data directory."""
    return project_root / "tests" / "fixtures"

@pytest.fixture
def kb_dir(project_root):
    """Return the knowledge base directory."""
    return project_root / "kb"

@pytest.fixture
def exports_dir(project_root):
    """Return the exports directory."""
    return project_root / "exports"
