"""Create Weaviate schema by delegating to autonomous.weaviate_client.ensure_schema

This avoids duplication and respects the centralized client handling.
"""

from data_layer.weaviate_client import ensure_schema


if __name__ == "__main__":
    ensure_schema()
    print("Schema ensure complete (see messages above).")

