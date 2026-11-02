"""
Canonical Epidemiological Taxonomy Registry for EpiSense.
Maintains curated classifications, aliases, ICD-10 codes, and outbreak eligibility
for all surveillance entities.
"""

from typing import Dict, List, Optional, Tuple
from episense.taxonomy.models import (
    CanonicalTaxonomyEntry,
    TaxonomyCategory,
    TaxonomyMatch,
)
from episense.schemas.alert import PathogenThreatTier


# Master Canonical Catalog
CANONICAL_ENTRIES: List[CanonicalTaxonomyEntry] = [
    # -------------------------------------------------------------------------
    # 1. INFECTIOUS DISEASES (Acute communicable pathogens)
    # -------------------------------------------------------------------------
    CanonicalTaxonomyEntry(
        canonical_id="nipah_virus",
        canonical_name="Nipah virus disease",
        category=TaxonomyCategory.INFECTIOUS_DISEASE,
        icd10_code=None,  # Unresolved (no unique 3-char ICD-10 code; WHO ICD-11 1D63 is specific to encephalitis; 1D65 is SARS)
        aliases=["nipah", "nipah virus", "nipah virus disease", "nipah infection", "henipavirus"],
        pathogen_tier=PathogenThreatTier.TIER_4_HIGH_CONSEQUENCE,
        can_cause_outbreak=True,
        transmission_mode="Zoonotic (Pteropus fruit bats) / close droplet / contaminated food",
        description="High-case-fatality zoonotic encephalitis and respiratory infection.",
    ),
    CanonicalTaxonomyEntry(
        canonical_id="henipavirus_encephalitis",
        canonical_name="Henipavirus encephalitis",
        category=TaxonomyCategory.INFECTIOUS_DISEASE,
        icd10_code="ICD11:1D63",  # Distinct clinical diagnosis code in ICD-11
        aliases=["henipavirus encephalitis", "nipah encephalitis"],
        pathogen_tier=PathogenThreatTier.TIER_4_HIGH_CONSEQUENCE,
        can_cause_outbreak=True,
        transmission_mode="Zoonotic / droplet transmission with documented central nervous system involvement",
        description="Confirmed acute encephalitis caused by Henipavirus (Nipah / Hendra).",
    ),
    CanonicalTaxonomyEntry(
        canonical_id="dengue",
        canonical_name="Dengue",
        category=TaxonomyCategory.INFECTIOUS_DISEASE,
        icd10_code="ICD10:A90",
        aliases=["dengue", "dengue fever", "suspected dengue", "dengue surges", "breakbone fever"],
        pathogen_tier=PathogenThreatTier.TIER_2_MODERATE,
        can_cause_outbreak=True,
        transmission_mode="Vector-borne (Aedes aegypti / albopictus)",
        description="Endemic arboviral flavivirus causing febrile illness and hemorrhagic manifestations.",
    ),
    CanonicalTaxonomyEntry(
        canonical_id="severe_dengue",
        canonical_name="Severe Dengue",
        category=TaxonomyCategory.INFECTIOUS_DISEASE,
        icd10_code="ICD10:A91",
        aliases=["severe dengue", "dengue hemorrhagic fever", "dhf", "dengue shock syndrome"],
        pathogen_tier=PathogenThreatTier.TIER_3_SEVERE,
        can_cause_outbreak=True,
        transmission_mode="Vector-borne (Aedes mosquitoes)",
        description="Severe manifestation of dengue featuring plasma leakage, shock, and organ impairment.",
    ),
    CanonicalTaxonomyEntry(
        canonical_id="chandipura",
        canonical_name="Chandipura virus",
        category=TaxonomyCategory.INFECTIOUS_DISEASE,
        icd10_code="ICD10:A85.8",
        aliases=["chandipura", "chandipura virus", "chpv", "chandipura vesiculovirus"],
        pathogen_tier=PathogenThreatTier.TIER_4_HIGH_CONSEQUENCE,
        can_cause_outbreak=True,
        transmission_mode="Vector-borne (Phlebotomine sandflies)",
        description="Rhabdovirus causing acute encephalitis with rapid clinical deterioration in pediatric patients.",
    ),
    CanonicalTaxonomyEntry(
        canonical_id="cholera",
        canonical_name="Cholera",
        category=TaxonomyCategory.INFECTIOUS_DISEASE,
        icd10_code="ICD10:A00",
        aliases=["cholera", "vibrio cholerae", "vibrio cholerae infection"],
        pathogen_tier=PathogenThreatTier.TIER_3_SEVERE,
        can_cause_outbreak=True,
        transmission_mode="Waterborne / foodborne ingestion",
        description="Acute toxigenic intestinal infection causing rapid dehydration and hypovolemic shock.",
    ),
    CanonicalTaxonomyEntry(
        canonical_id="leptospirosis",
        canonical_name="Leptospirosis",
        category=TaxonomyCategory.INFECTIOUS_DISEASE,
        icd10_code="ICD10:A27",
        aliases=["leptospirosis", "weil's disease", "rat fever"],
        pathogen_tier=PathogenThreatTier.TIER_3_SEVERE,
        can_cause_outbreak=True,
        transmission_mode="Zoonotic / exposure to water/soil contaminated with rodent urine",
        description="Bacterial spirochetal zoonosis common during post-monsoon flooding.",
    ),
    CanonicalTaxonomyEntry(
        canonical_id="scrub_typhus",
        canonical_name="Scrub Typhus",
        category=TaxonomyCategory.INFECTIOUS_DISEASE,
        icd10_code="ICD10:A75.3",
        aliases=["scrub typhus", "bush typhus", "orientia tsutsugamushi"],
        pathogen_tier=PathogenThreatTier.TIER_2_MODERATE,
        can_cause_outbreak=True,
        transmission_mode="Vector-borne (Leptotrombidium mite larvae / chiggers)",
        description="Rickettsial infection caused by Orientia tsutsugamushi.",
    ),
    CanonicalTaxonomyEntry(
        canonical_id="measles",
        canonical_name="Measles",
        category=TaxonomyCategory.INFECTIOUS_DISEASE,
        icd10_code="ICD10:B05",
        aliases=["measles", "rubeola"],
        pathogen_tier=PathogenThreatTier.TIER_2_MODERATE,
        can_cause_outbreak=True,
        transmission_mode="Airborne droplet / direct contact",
        description="Highly contagious morbillivirus infection in pediatric and unimmunized cohorts.",
    ),
    CanonicalTaxonomyEntry(
        canonical_id="avian_influenza",
        canonical_name="Avian influenza",
        category=TaxonomyCategory.INFECTIOUS_DISEASE,
        icd10_code="ICD10:J09",
        aliases=[
            "avian influenza", "bird flu", "avian influenza a(h5n1)",
            "avian influenza a(h9n2)", "h5n1", "h9n2",
        ],
        pathogen_tier=PathogenThreatTier.TIER_4_HIGH_CONSEQUENCE,
        can_cause_outbreak=True,
        transmission_mode="Direct contact with infected poultry / wild birds",
        description="High-pathogenicity influenza subtype with zoonotic spillover risk.",
    ),
    CanonicalTaxonomyEntry(
        canonical_id="kyasanur_forest_disease",
        canonical_name="Kyasanur Forest Disease",
        category=TaxonomyCategory.INFECTIOUS_DISEASE,
        icd10_code="ICD10:A98.2",
        aliases=["kyasanur forest disease", "kfd", "monkey fever"],
        pathogen_tier=PathogenThreatTier.TIER_3_SEVERE,
        can_cause_outbreak=True,
        transmission_mode="Vector-borne (Haemaphysalis ticks)",
        description="Flavivirus hemorrhagic fever endemic to Western Ghats forested regions.",
    ),
    CanonicalTaxonomyEntry(
        canonical_id="japanese_encephalitis",
        canonical_name="Japanese Encephalitis",
        category=TaxonomyCategory.INFECTIOUS_DISEASE,
        icd10_code="ICD10:A83.0",
        aliases=["japanese encephalitis", "je"],
        pathogen_tier=PathogenThreatTier.TIER_3_SEVERE,
        can_cause_outbreak=True,
        transmission_mode="Vector-borne (Culex tritaeniorhynchus mosquitoes / wading birds / swine)",
        description="Flavivirus neuroinvasive encephalitis with high neurological sequelae.",
    ),
    CanonicalTaxonomyEntry(
        canonical_id="malaria",
        canonical_name="Malaria",
        category=TaxonomyCategory.INFECTIOUS_DISEASE,
        icd10_code="ICD10:B54",
        aliases=["malaria", "plasmodium falciparum", "plasmodium vivax", "falciparum malaria", "vivax malaria"],
        pathogen_tier=PathogenThreatTier.TIER_2_MODERATE,
        can_cause_outbreak=True,
        transmission_mode="Vector-borne (Anopheles mosquitoes)",
        description="Parasitic protozoan infection caused by Plasmodium species.",
    ),
    CanonicalTaxonomyEntry(
        canonical_id="covid_19",
        canonical_name="COVID-19",
        category=TaxonomyCategory.INFECTIOUS_DISEASE,
        icd10_code="ICD10:U07.1",
        aliases=[
            "covid-19", "covid 19", "covid", "sars-cov-2", "coronavirus",
            "novel coronavirus", "coronavirus disease 2019", "coronavirus infection"
        ],
        pathogen_tier=PathogenThreatTier.TIER_2_MODERATE,
        can_cause_outbreak=True,
        transmission_mode="Respiratory aerosols / droplets",
        description="Acute respiratory coronavirus disease caused by SARS-CoV-2.",
    ),
    CanonicalTaxonomyEntry(
        canonical_id="zika",
        canonical_name="Zika virus disease",
        category=TaxonomyCategory.INFECTIOUS_DISEASE,
        icd10_code="ICD10:A92.8",
        aliases=["zika", "zika virus", "zika fever"],
        pathogen_tier=PathogenThreatTier.TIER_2_MODERATE,
        can_cause_outbreak=True,
        transmission_mode="Vector-borne (Aedes mosquitoes)",
        description="Arboviral infection associated with congenital microcephaly.",
    ),
    CanonicalTaxonomyEntry(
        canonical_id="chikungunya",
        canonical_name="Chikungunya",
        category=TaxonomyCategory.INFECTIOUS_DISEASE,
        icd10_code="ICD10:A92.0",
        aliases=["chikungunya", "chikungunya fever"],
        pathogen_tier=PathogenThreatTier.TIER_2_MODERATE,
        can_cause_outbreak=True,
        transmission_mode="Vector-borne (Aedes mosquitoes)",
        description="Alphaviral febrile illness featuring debilitating polyarthralgia.",
    ),
    CanonicalTaxonomyEntry(
        canonical_id="anthrax",
        canonical_name="Anthrax",
        category=TaxonomyCategory.INFECTIOUS_DISEASE,
        icd10_code="ICD10:A22",
        aliases=["anthrax", "cutaneous anthrax"],
        pathogen_tier=PathogenThreatTier.TIER_3_SEVERE,
        can_cause_outbreak=True,
        transmission_mode="Zoonotic spore contact / inhalation / ingestion",
        description="Bacillus anthracis bacterial infection.",
    ),
    CanonicalTaxonomyEntry(
        canonical_id="rabies",
        canonical_name="Rabies",
        category=TaxonomyCategory.INFECTIOUS_DISEASE,
        icd10_code="ICD10:A82",
        aliases=["rabies", "hydrophobia"],
        pathogen_tier=PathogenThreatTier.TIER_3_SEVERE,
        can_cause_outbreak=True,
        transmission_mode="Zoonotic animal bite / saliva contact",
        description="Fatal lyssavirus encephalomyelitis with 100% case-fatality once symptomatic.",
    ),
    CanonicalTaxonomyEntry(
        canonical_id="hepatitis_a",
        canonical_name="Acute Hepatitis A",
        category=TaxonomyCategory.INFECTIOUS_DISEASE,
        icd10_code="ICD10:B15",
        aliases=["hepatitis a", "acute hepatitis a", "hep a"],
        pathogen_tier=PathogenThreatTier.TIER_2_MODERATE,
        can_cause_outbreak=True,
        transmission_mode="Fecal-oral ingestion",
        description="Viral hepatitis resulting from contaminated water or food.",
    ),
    CanonicalTaxonomyEntry(
        canonical_id="hepatitis_e",
        canonical_name="Acute Hepatitis E",
        category=TaxonomyCategory.INFECTIOUS_DISEASE,
        icd10_code="ICD10:B17.2",
        aliases=["hepatitis e", "acute hepatitis e", "hep e"],
        pathogen_tier=PathogenThreatTier.TIER_2_MODERATE,
        can_cause_outbreak=True,
        transmission_mode="Fecal-oral ingestion",
        description="Enterically transmitted viral hepatitis with elevated risk in pregnancy.",
    ),
    CanonicalTaxonomyEntry(
        canonical_id="crimean_congo_hf",
        canonical_name="Crimean-Congo haemorrhagic fever",
        category=TaxonomyCategory.INFECTIOUS_DISEASE,
        icd10_code="ICD10:A98.0",
        aliases=[
            "crimean-congo haemorrhagic fever", "crimean-congo hemorrhagic fever",
            "cchf", "cchfv", "nairo virus", "orthonairovirus"
        ],
        pathogen_tier=PathogenThreatTier.TIER_4_HIGH_CONSEQUENCE,
        can_cause_outbreak=True,
        transmission_mode="Vector-borne (Hyalomma ticks) / livestock blood contact",
        description="Tick-borne nairovirus causing severe viral hemorrhagic fever.",
    ),
    CanonicalTaxonomyEntry(
        canonical_id="typhoid",
        canonical_name="Typhoid fever",
        category=TaxonomyCategory.INFECTIOUS_DISEASE,
        icd10_code="ICD10:A01.0",
        aliases=["typhoid", "typhoid fever", "enteric fever"],
        pathogen_tier=PathogenThreatTier.TIER_2_MODERATE,
        can_cause_outbreak=True,
        transmission_mode="Fecal-oral ingestion",
        description="Systemic bacterial infection caused by Salmonella enterica serovar Typhi.",
    ),
    CanonicalTaxonomyEntry(
        canonical_id="chickenpox",
        canonical_name="Chickenpox",
        category=TaxonomyCategory.INFECTIOUS_DISEASE,
        icd10_code="ICD10:B01.9",
        aliases=["chickenpox", "varicella"],
        pathogen_tier=PathogenThreatTier.TIER_1_MILD,
        can_cause_outbreak=True,
        transmission_mode="Airborne droplet / blister fluid",
        description="Varicella-zoster viral disease causing vesicular rash.",
    ),
    CanonicalTaxonomyEntry(
        canonical_id="mpox",
        canonical_name="Mpox",
        category=TaxonomyCategory.INFECTIOUS_DISEASE,
        icd10_code="ICD10:B04",
        aliases=["mpox", "monkeypox"],
        pathogen_tier=PathogenThreatTier.TIER_2_MODERATE,
        can_cause_outbreak=True,
        transmission_mode="Direct skin-to-skin contact / respiratory droplets",
        description="Zoonotic orthopoxvirus disease.",
    ),

    # -------------------------------------------------------------------------
    # 2. SYNDROMES (Clinical symptom complexes without identified pathogen)
    # -------------------------------------------------------------------------
    CanonicalTaxonomyEntry(
        canonical_id="acute_diarrheal_disease",
        canonical_name="Acute Diarrheal Disease",
        category=TaxonomyCategory.SYNDROME,
        icd10_code="ICD10:A09",
        aliases=["acute diarrheal disease", "acute diarrhoeal disease", "acute diarrhea", "acute diarrhoea", "add"],
        pathogen_tier=PathogenThreatTier.TIER_1_MILD,
        can_cause_outbreak=True,
        description="Syndromic presentation of acute water/electrolyte loss without established microbial etiology.",
    ),
    CanonicalTaxonomyEntry(
        canonical_id="acute_gastroenteritis",
        canonical_name="Acute Gastroenteritis",
        category=TaxonomyCategory.SYNDROME,
        icd10_code="ICD10:A09",
        aliases=["acute gastroenteritis", "gastroenteritis", "age"],
        pathogen_tier=PathogenThreatTier.TIER_1_MILD,
        can_cause_outbreak=True,
        description="Syndromic inflammation of gastrointestinal tract causing nausea, vomiting, and diarrhea.",
    ),
    CanonicalTaxonomyEntry(
        canonical_id="acute_encephalitis_syndrome",
        canonical_name="Acute Encephalitis Syndrome",
        category=TaxonomyCategory.SYNDROME,
        icd10_code="ICD10:A86",
        aliases=["acute encephalitis syndrome", "aes", "encephalitis syndrome"],
        pathogen_tier=PathogenThreatTier.TIER_3_SEVERE,
        can_cause_outbreak=True,
        description="Syndromic acute onset of fever and mental status change / seizures.",
    ),
    CanonicalTaxonomyEntry(
        canonical_id="viral_fever",
        canonical_name="Viral Fever",
        category=TaxonomyCategory.SYNDROME,
        icd10_code="ICD10:B34.9",
        aliases=["viral fever", "febrile illness", "acute febrile illness"],
        pathogen_tier=PathogenThreatTier.TIER_1_MILD,
        can_cause_outbreak=True,
        description="Undifferentiated febrile presentation.",
    ),
    CanonicalTaxonomyEntry(
        canonical_id="respiratory_disease",
        canonical_name="Acute Respiratory Illness",
        category=TaxonomyCategory.SYNDROME,
        icd10_code="ICD10:J98.9",
        aliases=["respiratory disease", "respiratory illness", "acute respiratory infection", "sari"],
        pathogen_tier=PathogenThreatTier.TIER_1_MILD,
        can_cause_outbreak=True,
        description="Broad syndromic classification for acute respiratory infections.",
    ),

    # -------------------------------------------------------------------------
    # 4. PUBLIC HEALTH EVENT CATEGORIES
    # -------------------------------------------------------------------------
    CanonicalTaxonomyEntry(
        canonical_id="food_poisoning",
        canonical_name="Food Poisoning",
        category=TaxonomyCategory.EVENT_CATEGORY,
        icd10_code="ICD10:A05.9",
        aliases=["food poisoning", "suspected food poisoning", "foodborne illness outbreak"],
        pathogen_tier=PathogenThreatTier.TIER_1_MILD,
        can_cause_outbreak=True,
        description="Acute illness resulting from consumption of contaminated foodstuffs.",
    ),
    CanonicalTaxonomyEntry(
        canonical_id="vector_borne_cluster",
        canonical_name="Vector-Borne Disease Cluster",
        category=TaxonomyCategory.EVENT_CATEGORY,
        icd10_code=None,
        aliases=["vector-borne disease", "vector-borne diseases"],
        pathogen_tier=PathogenThreatTier.TIER_2_MODERATE,
        can_cause_outbreak=True,
        description="Epidemiological aggregation of vector-transmitted illness.",
    ),

    # -------------------------------------------------------------------------
    # 5. NON-COMMUNICABLE CONDITIONS (Chronic / non-infectious pathology)
    # -------------------------------------------------------------------------
    CanonicalTaxonomyEntry(
        canonical_id="cardiovascular_disease",
        canonical_name="Cardiovascular Disease",
        category=TaxonomyCategory.NON_COMMUNICABLE_CONDITION,
        icd10_code="ICD10:I51.9",
        aliases=[
            "cardiovascular disease", "heart disease", "cvd", "coronary artery disease",
            "myocardial infarction", "hypertension", "stroke", "cardiac arrest"
        ],
        pathogen_tier=PathogenThreatTier.NONE,
        can_cause_outbreak=False,
        description="Chronic non-communicable circulatory pathology. Does not exhibit communicable transmission or epidemic clustering.",
    ),
    CanonicalTaxonomyEntry(
        canonical_id="chronic_lung_disease",
        canonical_name="Chronic Respiratory Disease",
        category=TaxonomyCategory.NON_COMMUNICABLE_CONDITION,
        icd10_code="ICD10:J98.9",
        aliases=["lung disease", "chronic obstructive pulmonary disease", "copd", "asthma"],
        pathogen_tier=PathogenThreatTier.NONE,
        can_cause_outbreak=False,
        description="Chronic non-communicable pulmonary condition.",
    ),
    CanonicalTaxonomyEntry(
        canonical_id="diabetes_mellitus",
        canonical_name="Diabetes Mellitus",
        category=TaxonomyCategory.NON_COMMUNICABLE_CONDITION,
        icd10_code="ICD10:E11",
        aliases=["diabetes", "diabetes mellitus"],
        pathogen_tier=PathogenThreatTier.NONE,
        can_cause_outbreak=False,
        description="Chronic metabolic disorder characterized by persistent hyperglycemia.",
    ),
]


class TaxonomyRegistry:
    """
    Registry for resolving mentions against standardized epidemiological taxonomy.
    """

    def __init__(self, entries: Optional[List[CanonicalTaxonomyEntry]] = None):
        self._entries: List[CanonicalTaxonomyEntry] = entries or CANONICAL_ENTRIES
        self._by_id: Dict[str, CanonicalTaxonomyEntry] = {}
        self._by_alias: Dict[str, CanonicalTaxonomyEntry] = {}

        for entry in self._entries:
            self._by_id[entry.canonical_id] = entry
            # Register canonical name
            self._by_alias[entry.canonical_name.lower().strip()] = entry
            # Register aliases
            for alias in entry.aliases:
                self._by_alias[alias.lower().strip()] = entry

    def resolve(self, mention: str) -> Optional[TaxonomyMatch]:
        """
        Resolves a raw text mention to a TaxonomyMatch.
        Checks exact alias first, then substring match.
        """
        clean = mention.strip().lower()
        if not clean:
            return None

        # 1. Exact alias lookup
        if clean in self._by_alias:
            entry = self._by_alias[clean]
            return TaxonomyMatch(
                raw_span=mention,
                canonical_id=entry.canonical_id,
                canonical_name=entry.canonical_name,
                category=entry.category,
                icd10_code=entry.icd10_code,
                matched_alias=clean,
                can_cause_outbreak=entry.can_cause_outbreak,
                pathogen_tier=entry.pathogen_tier,
            )

        # 2. Sub-phrase match (longest matching term first)
        sorted_aliases = sorted(self._by_alias.keys(), key=len, reverse=True)
        for alias in sorted_aliases:
            if alias in clean or clean in alias:
                entry = self._by_alias[alias]
                return TaxonomyMatch(
                    raw_span=mention,
                    canonical_id=entry.canonical_id,
                    canonical_name=entry.canonical_name,
                    category=entry.category,
                    icd10_code=entry.icd10_code,
                    matched_alias=alias,
                    can_cause_outbreak=entry.can_cause_outbreak,
                    pathogen_tier=entry.pathogen_tier,
                )

        return None

    def get_by_id(self, canonical_id: str) -> Optional[CanonicalTaxonomyEntry]:
        return self._by_id.get(canonical_id)

    def get_category(self, mention_or_id: str) -> Optional[TaxonomyCategory]:
        match = self.resolve(mention_or_id)
        if match:
            return match.category
        if mention_or_id in self._by_id:
            return self._by_id[mention_or_id].category
        return None

    def is_outbreak_eligible(self, mention_or_id: str) -> bool:
        """
        Returns False for non-communicable diseases, preventing inappropriate outbreak triage.
        """
        match = self.resolve(mention_or_id)
        if match:
            return match.can_cause_outbreak
        return True

    def list_entries(self, category: Optional[TaxonomyCategory] = None) -> List[CanonicalTaxonomyEntry]:
        if category:
            return [e for e in self._entries if e.category == category]
        return list(self._entries)

    def to_legacy_lexicon(self) -> Dict[str, Tuple[str, Optional[str]]]:
        """
        Generates backward-compatible DISEASE_LEXICON tuple mapping:
        term -> (canonical_name, icd10_code)
        """
        lex: Dict[str, Tuple[str, Optional[str]]] = {}
        for alias, entry in self._by_alias.items():
            lex[alias] = (entry.canonical_name, entry.icd10_code)
        return lex


# Global default instance
DEFAULT_TAXONOMY_REGISTRY = TaxonomyRegistry()
