"""OCR Extraction Integration for VERIFAI Backend.

Conforms to the backend integration contract used by backend/app/api/ocr.py.
Extracts both Visual Inspection Zone (VIZ) text and MRZ-derived identity data.
"""

import re
from typing import Dict, Any, List, Tuple
from ai.ocr_mrz.pipeline import process_passport
from ai.ocr_mrz.models import OCRLine


def _extract_viz_fields(ocr_lines: List[OCRLine]) -> Tuple[Dict[str, Any], Dict[str, float]]:
    """Extract printed visual inspection zone (VIZ) fields and per-field confidence."""
    texts = [l.text.strip() for l in ocr_lines]
    confs = {l.text.strip(): l.confidence for l in ocr_lines}

    fields: Dict[str, Any] = {}
    field_conf: Dict[str, float] = {}

    # 1. Date of Birth (visual)
    for i, t in enumerate(texts):
        if any(k in t.lower() for k in ['nacimiento', 'birth', 'naissance']):
            for candidate in texts[i:min(i + 4, len(texts))]:
                m = re.search(r'(\d{2})[-/.](\d{2})[-/.](\d{4})', candidate)
                if m:
                    d, mo, y = m.groups()
                    fields['dob'] = f"{y}-{mo}-{d}"
                    field_conf['dob'] = confs.get(candidate, 0.95)
                    break
                m2 = re.search(r'(\d{4})[-/.](\d{2})[-/.](\d{2})', candidate)
                if m2:
                    y, mo, d = m2.groups()
                    fields['dob'] = f"{y}-{mo}-{d}"
                    field_conf['dob'] = confs.get(candidate, 0.95)
                    break
            if 'dob' in fields:
                break

    # 2. Expiry Date (visual)
    for i, t in enumerate(texts):
        if any(k in t.lower() for k in ['caducidad', 'expiry', 'expiration']):
            for candidate in texts[i:min(i + 4, len(texts))]:
                m = re.search(r'(\d{2})[-/.](\d{2})[-/.](\d{4})', candidate)
                if m:
                    d, mo, y = m.groups()
                    fields['expiry'] = f"{y}-{mo}-{d}"
                    field_conf['expiry'] = confs.get(candidate, 0.95)
                    break
                m2 = re.search(r'(\d{4})[-/.](\d{2})[-/.](\d{2})', candidate)
                if m2:
                    y, mo, d = m2.groups()
                    fields['expiry'] = f"{y}-{mo}-{d}"
                    field_conf['expiry'] = confs.get(candidate, 0.95)
                    break
            if 'expiry' in fields:
                break

    # 3. Surname & Given Names
    for i, t in enumerate(texts):
        clean_t = re.sub(r'[^a-z]', '', t.lower())
        if 'apellidos' in clean_t or 'surname' in clean_t or ('nom' in clean_t and 'nombre' not in clean_t):
            for candidate in texts[i + 1:min(i + 3, len(texts))]:
                cand_clean = re.sub(r'[^a-z]', '', candidate.lower())
                if not any(h in cand_clean for h in ['nombre', 'given', 'prenoms', 'sex', 'tipo', 'type', 'passport']):
                    if candidate.replace(' ', '').isalpha():
                        fields['surname'] = candidate
                        field_conf['surname'] = confs.get(candidate, 0.95)
                        break
            if 'surname' in fields:
                break

    for i, t in enumerate(texts):
        clean_t = re.sub(r'[^a-z]', '', t.lower())
        if any(k in clean_t for k in ['nombre', 'givennames', 'prenoms']):
            for candidate in texts[i + 1:min(i + 3, len(texts))]:
                cand_clean = re.sub(r'[^a-z]', '', candidate.lower())
                if not any(h in cand_clean for h in ['nacionalidad', 'nationality', 'sex', 'fecha', 'birth', 'date']):
                    if candidate.replace(' ', '').isalpha():
                        fields['given_names'] = candidate
                        field_conf['given_names'] = confs.get(candidate, 0.95)
                        break
            if 'given_names' in fields:
                break

    if 'surname' in fields and 'given_names' in fields:
        fields['name'] = f"{fields['surname']} {fields['given_names']}"
        field_conf['name'] = round((field_conf['surname'] + field_conf['given_names']) / 2.0, 3)
    elif 'surname' in fields:
        fields['name'] = fields['surname']
        field_conf['name'] = field_conf['surname']

    # 4. Document / Passport Number
    for i, t in enumerate(texts):
        clean_t = re.sub(r'[^a-z]', '', t.lower())
        if any(k in clean_t for k in ['passportno', 'pasaporteno', 'passeportno', 'docno', 'documentno']):
            for cand in texts[i:min(i + 5, len(texts))]:
                cand_clean = cand.strip().upper()
                if re.match(r'^[A-Z0-9]{8,10}$', cand_clean) and not any(w in cand_clean for w in ['PASSPORT', 'PASAPORTE', 'PASSEPORT']):
                    fields['doc_number'] = cand_clean
                    field_conf['doc_number'] = confs.get(cand, 0.95)
                    break
            if 'doc_number' in fields:
                break

    # If doc_number not found near label, check across all lines for standard passport regex
    if 'doc_number' not in fields:
        for t in texts:
            t_clean = t.strip().upper()
            if re.match(r'^[A-Z]{1,2}[0-9]{7,8}$', t_clean) or re.match(r'^[0-9]{9}$', t_clean):
                if not t_clean.startswith('P<') and not t_clean.startswith('I<'):
                    fields['doc_number'] = t_clean
                    field_conf['doc_number'] = confs.get(t, 0.95)
                    break

    # 5. Nationality & Sex
    for i, t in enumerate(texts):
        clean_t = re.sub(r'[^a-z]', '', t.lower())
        if any(k in clean_t for k in ['nacionalidad', 'nationality', 'nationalit']):
            for cand in texts[i + 1:min(i + 4, len(texts))]:
                cand_upper = cand.strip().upper()
                if any(cand_upper.startswith(c) for c in ['ESPA', 'SPANISH', 'ESP', 'UTO', 'UTOPIA', 'USA', 'IND', 'GBR', 'FRA', 'DEU']):
                    fields['nationality'] = cand_upper
                    field_conf['nationality'] = confs.get(cand, 0.95)
                    break
        if any(k in clean_t for k in ['sexo', 'sex', 'sexe']):
            for cand in texts[i:min(i + 4, len(texts))]:
                cand_upper = cand.strip().upper()
                if cand_upper in ['M', 'F', 'X']:
                    fields['sex'] = cand_upper
                    field_conf['sex'] = confs.get(cand, 0.95)
                    break

    # 6. Personal Number / ID Number
    for i, t in enumerate(texts):
        clean_t = re.sub(r'[^a-z0-9]', '', t.lower())
        if 'idno' in clean_t or 'personalno' in clean_t:
            for cand in texts[i:min(i + 4, len(texts))]:
                cand_upper = cand.strip().upper()
                if re.match(r'^[A-Z0-9]{9,15}$', cand_upper) and cand_upper != fields.get('doc_number'):
                    fields['personal_number'] = cand_upper
                    field_conf['personal_number'] = confs.get(cand, 0.95)
                    break

    return fields, field_conf


def run_ocr(image_path: str, engine_type: str = "paddle") -> Dict[str, Any]:
    """Run OCR extraction and field mapping for backend document processing.

    Args:
        image_path: Path to passport/document image.
        engine_type: OCR backend ('paddle' or 'mock').

    Returns:
        Dictionary adhering to backend OCR data contract:
        - structured_fields: dict (name, dob, doc_number, nationality, expiry)
        - field_confidence: dict of per-field confidence scores
        - raw_text: extracted raw text representation
        - _stub: bool
    """
    response = process_passport(image_path, engine_type=engine_type)

    ocr_lines = response.raw_ocr_lines or []
    default_conf = response.ocr.confidence if response.ocr else 0.90

    # 1. Extract visual inspection zone fields
    viz_fields, viz_confs = _extract_viz_fields(ocr_lines) if ocr_lines else ({}, {})

    # 2. Extract full raw text
    if ocr_lines:
        raw_text = "\n".join(l.text for l in ocr_lines)
    elif response.raw_mrz:
        raw_text = f"{response.raw_mrz.get('line1', '')}\n{response.raw_mrz.get('line2', '')}"
    else:
        raw_text = ""

    # 3. Fallback to MRZ parsed fields if visual field was not detected
    structured = dict(viz_fields)
    confidence_dict = dict(viz_confs)

    if response.identity:
        ident = response.identity
        if "doc_number" not in structured and ident.passport_number:
            structured["doc_number"] = ident.passport_number
            confidence_dict["doc_number"] = default_conf
        if "dob" not in structured and ident.date_of_birth:
            structured["dob"] = ident.date_of_birth
            confidence_dict["dob"] = default_conf
        if "expiry" not in structured and ident.expiry_date:
            structured["expiry"] = ident.expiry_date
            confidence_dict["expiry"] = default_conf
        if "name" not in structured and ident.name:
            structured["name"] = ident.name
            confidence_dict["name"] = default_conf
        if "nationality" not in structured and ident.nationality:
            structured["nationality"] = ident.nationality
            confidence_dict["nationality"] = default_conf
        if "sex" not in structured and ident.sex:
            structured["sex"] = ident.sex
            confidence_dict["sex"] = default_conf
        if "issuing_state" not in structured and ident.issuing_state:
            structured["issuing_state"] = ident.issuing_state
            confidence_dict["issuing_state"] = default_conf
        if "personal_number" not in structured and ident.personal_number:
            structured["personal_number"] = ident.personal_number
            confidence_dict["personal_number"] = default_conf

    # Always ensure core keys exist with at least None / empty if not found
    for key in ["name", "dob", "doc_number", "nationality", "expiry"]:
        if key not in structured:
            structured[key] = None
            confidence_dict[key] = 0.0

    return {
        "structured_fields": structured,
        "field_confidence": confidence_dict,
        "raw_text": raw_text,
        "_stub": False,
    }
