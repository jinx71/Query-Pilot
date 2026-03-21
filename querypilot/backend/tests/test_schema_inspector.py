"""Integration tests for schema introspection."""
import pytest

from app.schema_inspector import clear_schema_cache, get_schema

pytestmark = pytest.mark.requires_db


@pytest.fixture(autouse=True)
def _fresh_cache():
    clear_schema_cache()
    yield
    clear_schema_cache()


def test_all_tables_discovered():
    tree = get_schema()["schema_tree"]
    names = {t["name"] for t in tree["tables"]}
    assert names == {
        "products", "equipment", "operators", "batches", "qc_tests", "deviations"
    }


def test_foreign_keys_are_captured():
    tree = get_schema()["schema_tree"]
    batches = next(t for t in tree["tables"] if t["name"] == "batches")
    refs = {c["name"]: c.get("references") for c in batches["columns"]}
    assert refs["product_id"] == "products.id"
    assert refs["equipment_id"] == "equipment.id"


def test_low_cardinality_columns_get_sample_values():
    tree = get_schema()["schema_tree"]
    batches = next(t for t in tree["tables"] if t["name"] == "batches")
    status_col = next(c for c in batches["columns"] if c["name"] == "status")
    assert set(status_col["sample_values"]) <= {"released", "rejected", "quarantine"}
    assert "released" in status_col["sample_values"]


def test_prompt_contains_tables_and_values():
    prompt = get_schema()["schema_prompt"]
    assert "TABLE batches" in prompt
    assert "REFERENCES products.id" in prompt
    assert "values:" in prompt  # enum sampling shows up in the prompt
