import csv
import re
import os

UPLOAD_DIR = "/sessions/admiring-nifty-goldberg/mnt/uploads"
OUTPUT_DIR = "/sessions/admiring-nifty-goldberg/mnt/outputs/categorised_gold_standards"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def categorise_af(term):
    t = term.lower().strip()
    # Core diagnosis
    if t in ("atrial fibrillation", "atrial flutter", "atrial fibrillation and flutter"):
        return "D"
    return "S"  # All others are subtypes

def categorise_pmr(term):
    t = term.lower().strip()
    if "history" in t:
        return "H"
    if "giant cell arteritis" in t:
        return "S"  # Related condition / overlap
    return "D"

def categorise_ms(term):
    t = term.lower().strip()
    if "specialised services" in t or "administration" in t:
        return "P"
    if "history" in t:
        return "H"
    if any(x in t for x in ["dementia", "uveitis", "optic neuritis", "autonomic",
                             "hemichorea", "myelitis due to", "neuropathic pain",
                             "uhthoff"]):
        return "C"
    if "ichthyosis" in t or "factor viii" in t:
        return "S"  # Syndromic
    # Core MS and subtypes
    if any(x in t for x in ["multiple sclerosis", "concentric sclerosis"]):
        if t in ("multiple sclerosis", "multiple sclerosis nos"):
            return "D"
        return "S"
    return "S"  # Default for MS

def categorise_t2dm_cod(term):
    t = term.lower().strip()
    # Core diagnosis
    if t in ("diabetes mellitus type 2",):
        return "D"
    # Diagnosis qualifiers
    if any(x in t for x in ["without retinopathy", "without complication",
                             "insulin treated", "uncontrolled", "brittle",
                             "in remission"]):
        return "S"
    # Everything else is complication
    return "C"

def categorise_t2dm_audit(term):
    t = term.lower().strip()
    # Core diagnosis
    if t in ("diabetes mellitus type 2", "diabetes mellitus type 2 in obese",
             "diabetes mellitus type 2 in nonobese",
             "diabetes mellitus autosomal dominant type 2"):
        return "D"
    # History/Review/Admin
    if any(x in t for x in ["history of", "review", "diabetic on insulin",
                             "diabetic on diet only", "dietary review"]):
        return "H"
    # Diagnosis qualifiers (status/control/treatment)
    if any(x in t for x in ["without retinopathy", "without complication",
                             "insulin treated", "uncontrolled", "brittle",
                             "in remission", "well controlled", "controlled by diet",
                             "pre-existing type 2"]):
        return "S"
    # Pregnancy
    if any(x in t for x in ["pregnancy", "childbirth"]):
        return "S"
    # Anatomical detail (laterality in retinopathy)
    if any(x in t for x in ["left eye", "right eye", "bilateral"]):
        return "A"
    # Complications
    return "C"

def categorise_asthma(term):
    t = term.lower().strip()
    # Exacerbation
    if "exacerbation" in t:
        return "V"
    # Severity/Control
    if any(x in t for x in ["controlled", "uncontrolled",
                             "mild persistent", "moderate persistent",
                             "severe persistent", "intermittent asthma well",
                             "mild asthma", "moderate asthma", "severe asthma",
                             "intermittent asthma", "intermittent allergic asthma",
                             "severe controlled", "near fatal", "life threatening",
                             "brittle"]):
        return "V"
    # Occupational/Substance
    if any(x in t for x in ["millers", "feather", "flax", "printer", "meat-wrapper",
                             "baker", "detergent", "tea-maker", "colophony",
                             "sulfite", "isocyanate", "platinum", "cheese",
                             "wood dust", "weaver", "chemical-induced",
                             "drug-induced", "substance induced", "aspirin",
                             "byssinosis", "occupational"]):
        return "S"
    # Pregnancy
    if "pregnancy" in t or "childbirth" in t or "complicating" in t:
        return "S"
    # Core diagnosis/subtypes
    return "D"

def categorise_chd(term):
    t = term.lower().strip()
    # History
    if t.startswith("history of"):
        return "H"
    # Procedure/Planning
    if any(x in t for x in ["planned", "repeated"]):
        return "P"
    # Post-MI complications
    if any(x in t for x in ["due to and following acute myocardial",
                             "following acute myocardial",
                             "complication following",
                             "post-infarction", "postmyocardial infarction syndrome",
                             "post infarct angina",
                             "mural thrombus", "ventricular aneurysm",
                             "pulmonary embolism due to and following",
                             "arrhythmia due to and following",
                             "cardiogenic shock unrelated",
                             "pericardial effusion following"]):
        return "C"
    # Anatomical detail (vessel-segment stenosis/occlusion)
    if re.search(r"stenosis of (proximal|mid|distal|ostium|marginal|posterior)", t):
        return "A"
    if re.search(r"occlusion of (proximal|mid|distal|obtuse|posterior|diagonal|septal|intermediate)", t):
        return "A"
    if "occlusion of anterior descending" in t:
        return "A"
    if "occlusion of circumflex" in t and "acute st" not in t:
        return "A"
    # STEMI by specific vessel occlusion (these are diagnosis WITH anatomical detail)
    if "acute st segment elevation" in t and "due to occlusion" in t:
        return "A"
    # Ischemia by specific region
    if re.search(r"ischemia of (anterior|apical|lateral|posterior|inferior|myocardium of)", t):
        return "A"
    # Bypass graft disease
    if any(x in t for x in ["bypass graft", "coronary graft"]):
        return "S"
    # Arteriosclerosis/Atherosclerosis (subtypes of CHD)
    if any(x in t for x in ["arteriosclerosis", "atherosclerosis", "atheroma",
                             "coronary artery sclerosis"]):
        return "S"
    # Core stenosis/occlusion (non-segmental)
    if any(x in t for x in ["stenosis of coronary", "stenosis of right coronary",
                             "stenosis of left coronary", "stenosis of circumflex",
                             "stenosis of anterior descending",
                             "coronary occlusion", "total occlusion"]):
        return "S"
    # Angina
    if any(x in t for x in ["angina", "anginosus", "preinfarction syndrome",
                             "impending infarction"]):
        return "S"
    # Acute MI (diagnosable conditions)
    if "acute myocardial infarction" in t or "acute st segment" in t or \
       "acute non-st" in t or "acute q wave" in t or "acute non-q wave" in t or \
       "acute infarction" in t or "acute anteroseptal" in t or \
       "acute anteroapical" in t or "acute coronary" in t or \
       "acute subendocardial" in t:
        return "D"
    # Old/subsequent MI
    if any(x in t for x in ["old myocardial", "old infarct", "old anterior",
                             "old inferior", "old lateral", "old posterior",
                             "subsequent myocardial", "subsequent st segment",
                             "subsequent non-st", "past myocardial",
                             "recent myocardial", "new myocardial",
                             "silent myocardial infarction",
                             "first myocardial"]):
        return "S"
    # Core IHD/CHD diagnoses
    if any(x in t for x in ["ischemic heart disease", "ischaemic heart disease",
                             "coronary heart disease", "myocardial infarction",
                             "coronary artery disease", "disorder of coronary",
                             "myocardial ischemia", "myocardial ischaemia",
                             "coronary thrombosis", "coronary insufficiency",
                             "coronary syndrome",
                             "single coronary vessel", "double coronary vessel",
                             "triple vessel", "multi vessel",
                             "left main coronary artery disease",
                             "microvascular"]):
        return "D"
    # Ischemia general
    if any(x in t for x in ["ischemi", "ischaemi"]):
        return "D"
    # Remaining MI-related
    if "myocardial infarction" in t or "infarction" in t or "infarct" in t:
        return "D"
    # Default
    return "D"

def categorise_hypothyroidism(term):
    t = term.lower().strip()
    # Syndromes with hypothyroidism as a feature
    if any(x in t for x in ["choanal atresia", "obesity, colitis",
                             "bamforth", "short stature.*thyroid",
                             "pseudohypertrophy", "x-linked central congenital"]):
        return "S"
    if "syndrome" in t and "hypothyroidism" not in t.split("syndrome")[0].split(",")[-1]:
        return "S"
    # Core diagnosis
    if t in ("hypothyroidism", "primary hypothyroidism", "goiter"):
        return "D"
    # Myxedema (clinical manifestation)
    if "myxedema" in t or "myxoedema" in t:
        return "C"
    # Everything else is a subtype
    return "S"


# Process each file
FILES = {
    "afib": ("nhsd-primary-care-domain-refsets-afib_cod-20250912.csv", categorise_af, "afib_cod_categorised.csv"),
    "pmr": ("nhsd-primary-care-domain-refsets-pmr_cod-20250912.csv", categorise_pmr, "pmr_cod_categorised.csv"),
    "ms": ("nhsd-primary-care-domain-refsets-ms_cod-20250912.csv", categorise_ms, "ms_cod_categorised.csv"),
    "t2dm": ("nhsd-primary-care-domain-refsets-dmtype2_cod-20250912.csv", categorise_t2dm_cod, "dmtype2_cod_categorised.csv"),
    "t2dm_audit": ("nhsd-primary-care-domain-refsets-dmtype2audit_cod-20250912 (2).csv", categorise_t2dm_audit, "dmtype2audit_cod_categorised.csv"),
    "asthma": ("nhsd-primary-care-domain-refsets-ast_cod-20250912.csv", categorise_asthma, "ast_cod_categorised.csv"),
    "chd": ("nhsd-primary-care-domain-refsets-chd_cod-20250912.csv", categorise_chd, "chd_cod_categorised.csv"),
    "thy": ("nhsd-primary-care-domain-refsets-thy_cod-20250912.csv", categorise_hypothyroidism, "thy_cod_categorised.csv"),
}

CATEGORY_LABELS = {
    "D": "Diagnosis",
    "S": "Subtype",
    "V": "Severity/Exacerbation",
    "C": "Complication",
    "A": "Anatomical detail",
    "H": "History",
    "P": "Procedure/Admin"
}

for key, (infile, categoriser, outfile) in FILES.items():
    inpath = os.path.join(UPLOAD_DIR, infile)
    outpath = os.path.join(OUTPUT_DIR, outfile)
    
    counts = {}
    rows = []
    with open(inpath, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            code = row["code"].strip()
            term = row["term"].strip()
            cat = categoriser(term)
            rows.append({"code": code, "term": term, "category": cat})
            counts[cat] = counts.get(cat, 0) + 1
    
    with open(outpath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["code", "term", "category"])
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"\n{'='*60}")
    print(f"{key.upper()} ({outfile}) — {len(rows)} codes")
    print(f"{'='*60}")
    for cat in ["D", "S", "V", "C", "A", "H", "P"]:
        if cat in counts:
            print(f"  {cat} ({CATEGORY_LABELS[cat]}): {counts[cat]}")

