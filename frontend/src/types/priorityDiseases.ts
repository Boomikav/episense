/**
 * Authoritative 8 Priority Disease Registry for EpiSense Research Surveillance (Frontend).
 * Matches the canonical backend registry in episense.taxonomy.priority.
 */

export interface PriorityDiseaseInfo {
  id: string;
  name: string;
  icd10: string;
  category: "infectious_disease" | "syndrome";
  tier: "tier_1_mild" | "tier_2_moderate" | "tier_3_severe" | "tier_4_high_consequence";
  transmission: string;
  aliases: string[];
}

export const CANONICAL_PRIORITY_DISEASES: PriorityDiseaseInfo[] = [
  {
    id: "dengue",
    name: "Dengue",
    icd10: "ICD10:A90",
    category: "infectious_disease",
    tier: "tier_2_moderate",
    transmission: "Vector-borne (Aedes mosquitoes)",
    aliases: ["dengue", "dengue fever", "suspected dengue", "breakbone fever", "severe dengue", "dhf"],
  },
  {
    id: "malaria",
    name: "Malaria",
    icd10: "ICD10:B54",
    category: "infectious_disease",
    tier: "tier_2_moderate",
    transmission: "Vector-borne (Anopheles mosquitoes)",
    aliases: ["malaria", "plasmodium falciparum", "plasmodium vivax", "falciparum malaria", "vivax malaria"],
  },
  {
    id: "chikungunya",
    name: "Chikungunya",
    icd10: "ICD10:A92.0",
    category: "infectious_disease",
    tier: "tier_2_moderate",
    transmission: "Vector-borne (Aedes mosquitoes)",
    aliases: ["chikungunya", "chikungunya fever", "chikv"],
  },
  {
    id: "leptospirosis",
    name: "Leptospirosis",
    icd10: "ICD10:A27",
    category: "infectious_disease",
    tier: "tier_3_severe",
    transmission: "Zoonotic / floodwater contamination",
    aliases: ["leptospirosis", "weil's disease", "rat fever"],
  },
  {
    id: "cholera",
    name: "Cholera",
    icd10: "ICD10:A00",
    category: "infectious_disease",
    tier: "tier_3_severe",
    transmission: "Waterborne / foodborne (Vibrio cholerae)",
    aliases: ["cholera", "vibrio cholerae", "vibrio cholerae infection"],
  },
  {
    id: "acute_diarrhoeal_disease",
    name: "Acute Diarrhoeal Disease",
    icd10: "ICD10:A09",
    category: "syndrome",
    tier: "tier_1_mild",
    transmission: "Fecal-oral ingestion / waterborne",
    aliases: ["acute diarrhoeal disease", "acute diarrheal disease", "acute diarrhea", "acute diarrhoea", "add"],
  },
  {
    id: "japanese_encephalitis",
    name: "Japanese Encephalitis",
    icd10: "ICD10:A83.0",
    category: "infectious_disease",
    tier: "tier_3_severe",
    transmission: "Vector-borne (Culex mosquitoes)",
    aliases: ["japanese encephalitis", "je"],
  },
  {
    id: "scrub_typhus",
    name: "Scrub Typhus",
    icd10: "ICD10:A75.3",
    category: "infectious_disease",
    tier: "tier_2_moderate",
    transmission: "Vector-borne (Chigger mites)",
    aliases: ["scrub typhus", "bush typhus", "orientia tsutsugamushi"],
  },
];

export const PRIORITY_DISEASE_NAMES = CANONICAL_PRIORITY_DISEASES.map((d) => d.name);

export function isPriorityDisease(nameOrKey: string): boolean {
  const clean = (nameOrKey || "").toLowerCase().trim();
  return CANONICAL_PRIORITY_DISEASES.some(
    (d) => d.id === clean || d.name.toLowerCase() === clean || d.aliases.some((a) => clean.includes(a) || a.includes(clean))
  );
}

export function resolveCanonicalPriorityName(nameOrKey: string): string | null {
  const clean = (nameOrKey || "").toLowerCase().trim();
  for (const d of CANONICAL_PRIORITY_DISEASES) {
    if (d.id === clean || d.name.toLowerCase() === clean || d.aliases.some((a) => clean === a || clean.includes(a))) {
      return d.name;
    }
  }
  return null;
}
