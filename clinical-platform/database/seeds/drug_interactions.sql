-- database/seeds/drug_interactions.sql
-- This seeds a small set of well-known interactions for the demo.
-- Real production would source from curated pharmacology databases.

-- First, ensure the drug_concepts exist (idempotent)
INSERT INTO drug_concepts (rxnorm_cui, name, drug_class) VALUES
    ('197361', 'Warfarin', 'Anticoagulant'),
    ('6809', 'Metformin', 'Biguanide antihyperglycemic'),
    ('29046', 'Lisinopril', 'ACE inhibitor'),
    ('36556', 'Simvastatin', 'HMG-CoA reductase inhibitor'),
    ('152923', 'Atorvastatin', 'HMG-CoA reductase inhibitor'),
    ('68091', 'Ibuprofen', 'NSAID'),
    ('161', 'Acetaminophen', 'Analgesic'),
    ('2556', 'Aspirin', 'NSAID / Antiplatelet'),
    ('208161', 'Amiodarone', 'Antiarrhythmic'),
    ('10180', 'Ciprofloxacin', 'Fluoroquinolone antibiotic')
ON CONFLICT (rxnorm_cui) DO NOTHING;

-- Map CUI -> ID for FK inserts
DO $$
DECLARE
    warfarin_id UUID;
    metformin_id UUID;
    lisinopril_id UUID;
    simvastatin_id UUID;
    atorvastatin_id UUID;
    ibuprofen_id UUID;
    acetaminophen_id UUID;
    aspirin_id UUID;
    amiodarone_id UUID;
    ciprofloxacin_id UUID;
BEGIN
    SELECT id INTO warfarin_id FROM drug_concepts WHERE rxnorm_cui = '197361';
    SELECT id INTO metformin_id FROM drug_concepts WHERE rxnorm_cui = '6809';
    SELECT id INTO lisinopril_id FROM drug_concepts WHERE rxnorm_cui = '29046';
    SELECT id INTO simvastatin_id FROM drug_concepts WHERE rxnorm_cui = '36556';
    SELECT id INTO atorvastatin_id FROM drug_concepts WHERE rxnorm_cui = '152923';
    SELECT id INTO ibuprofen_id FROM drug_concepts WHERE rxnorm_cui = '68091';
    SELECT id INTO acetaminophen_id FROM drug_concepts WHERE rxnorm_cui = '161';
    SELECT id INTO aspirin_id FROM drug_concepts WHERE rxnorm_cui = '2556';
    SELECT id INTO amiodarone_id FROM drug_concepts WHERE rxnorm_cui = '208161';
    SELECT id INTO ciprofloxacin_id FROM drug_concepts WHERE rxnorm_cui = '10180';

    INSERT INTO drug_interactions (drug_a_id, drug_b_id, severity, mechanism, clinical_significance, evidence_source, evidence_strength) VALUES
        (aspirin_id, ibuprofen_id, 'moderate', 'Both NSAIDs; reduced antiplatelet effect of aspirin', 'May reduce cardioprotective effect', 'FDA labeling', 'established'),
        (aspirin_id, warfarin_id, 'major', 'Additive anticoagulant/antiplatelet effects', 'Significantly increased bleeding risk', 'FDA labeling', 'established'),
        (ibuprofen_id, warfarin_id, 'major', 'NSAID-induced platelet inhibition + warfarin anticoagulation', 'Increased GI bleeding risk', 'DrugBank', 'established'),
        (simvastatin_id, amiodarone_id, 'major', 'CYP3A4 inhibition increases simvastatin levels', 'Increased risk of rhabdomyolysis', 'FDA labeling', 'established'),
        (atorvastatin_id, ciprofloxacin_id, 'moderate', 'CYP3A4 inhibition increases statin levels', 'Increased myopathy risk', 'DrugBank', 'established'),
        (lisinopril_id, ibuprofen_id, 'moderate', 'NSAIDs reduce ACE inhibitor antihypertensive effect', 'Reduced BP control, possible renal impairment', 'DrugBank', 'established'),
        (metformin_id, ciprofloxacin_id, 'moderate', 'Possible additive glucose dysregulation', 'Monitor blood glucose', 'DrugBank', 'theoretical'),
        (acetaminophen_id, warfarin_id, 'moderate', 'Possible CYP2C9 interaction at high doses', 'Increased INR with chronic high-dose APAP', 'DrugBank', 'case_reports')
    ON CONFLICT (drug_a_id, drug_b_id) DO NOTHING;
END $$;
