import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.pipeline import calculate
from app.samples import load_sample


@pytest.fixture
def clean_data():
    return load_sample("clean")


@pytest.fixture
def dirty_data():
    return load_sample("dirty")


@pytest.fixture
def clean(clean_data):
    return calculate(clean_data)


@pytest.fixture
def dirty(dirty_data):
    return calculate(dirty_data)


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(tmp_path / "archive.sqlite3")) as connection:
        yield connection
