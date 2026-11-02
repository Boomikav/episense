"""
Tests verifying abstract interfaces and contracts.
"""

import pytest
from uuid import uuid4
from episense.interfaces.nlp import EntityExtractor
from episense.schemas.entity import Entity, EntityType


def test_interface_cannot_be_instantiated_directly():
    """Verify that abstract classes cannot be directly instantiated."""
    with pytest.raises(TypeError):
        EntityExtractor()


def test_compliant_mock_implementation():
    """Verify that a compliant class satisfies the interface."""
    class DummyExtractor(EntityExtractor):
        def extract(self, text, document_id):
            return [
                Entity(
                    document_id=document_id,
                    entity_type=EntityType.DISEASE,
                    text_span="dengue",
                    start_char=0,
                    end_char=6,
                )
            ]

    extractor = DummyExtractor()
    doc_id = uuid4()
    entities = extractor.extract("dengue outbreak", doc_id)
    assert len(entities) == 1
    assert entities[0].text_span == "dengue"
