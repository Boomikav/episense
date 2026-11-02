"""
Epidemiological Taxonomy API Routes for EpiSense.
Provides access to canonical classifications, categories, and term resolution.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Query

from episense.taxonomy.models import CanonicalTaxonomyEntry, TaxonomyCategory, TaxonomyMatch
from episense.taxonomy.registry import DEFAULT_TAXONOMY_REGISTRY
from episense.taxonomy.priority import PRIORITY_DISEASES, PriorityDiseaseMetadata, list_priority_disease_metadata

router = APIRouter(prefix="/api/v1/taxonomy", tags=["Taxonomy"])


@router.get("/priority", response_model=List[PriorityDiseaseMetadata])
async def list_priority_diseases() -> List[PriorityDiseaseMetadata]:
    """Returns the canonical 8 priority research surveillance diseases registry."""
    return PRIORITY_DISEASES


@router.get("", response_model=List[CanonicalTaxonomyEntry])
async def list_taxonomy(
    category: Optional[TaxonomyCategory] = Query(None, description="Filter by taxonomy category")
) -> List[CanonicalTaxonomyEntry]:
    """Returns canonical disease, pathogen, syndrome, and condition classifications."""
    return DEFAULT_TAXONOMY_REGISTRY.list_entries(category=category)


@router.get("/resolve", response_model=Optional[TaxonomyMatch])
async def resolve_term(
    query: str = Query(..., description="Entity term or phrase to resolve against taxonomy")
) -> Optional[TaxonomyMatch]:
    """Resolves an entity text span against the canonical taxonomy."""
    return DEFAULT_TAXONOMY_REGISTRY.resolve(query)
