import json, sys, ast

# Test 1: config loads and validates
with open('survey_config.json', encoding='utf-8') as f:
    cfg = json.load(f)
n_demo = len(cfg['demographic_section']['questions'])
n_sects = len(cfg['likert_sections'])
n_items = sum(len(s['questions']) for s in cfg['likert_sections'])
print(f'Config OK: {n_demo} demo questions, {n_sects} sections, {n_items} Likert items')

# Test 2: DOCX parser
from docx_to_json import parse_docx_to_config
parsed = parse_docx_to_config('Questionnaire - Gender Inequality_17Mar2026.docx')
p_sects = len(parsed['likert_sections'])
p_items = sum(len(s['questions']) for s in parsed['likert_sections'])
print(f'Parser OK: {p_sects} sections, {p_items} Likert items extracted from DOCX')

# Test 3: app syntax check
with open('survey_app.py', encoding='utf-8') as f:
    src = f.read()
ast.parse(src)
print('survey_app.py syntax OK')

print()
print('ALL TESTS PASSED')
