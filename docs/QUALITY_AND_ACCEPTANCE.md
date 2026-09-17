# translatePSD — Quality and Acceptance

This page explains how to assess an output. It does not change translation logic or certify model quality.

## Separate the checks

| Mechanism | Repository evidence | What it does not establish |
| --- | --- | --- |
| Terminology dictionaries | section_dictionary.py, normative_dictionary.py and dictionary seed/template files | Legal rights to a source glossary or automatic standards compliance |
| Translation memory | translation_memory.py; current tracked memory is an empty JSON object | Measured accuracy, efficiency or customer usage |
| Routing/deduplication | translation_router.py and translator_hybrid.py | A successful translation when a provider fails |
| Rule/term validators | validator.py, validator_sections.py, validator_snrk.py | A complete regression test suite or guaranteed engineering correctness |
| Review flags/normalization | normalizer.py and post_translate_fix.py | A complete semantic review of every sentence |
| Optional LLM QC | llm_validator.py and Streamlit controls | Independent model-quality validation |
| Metrics/audit helpers | translation_metrics.py and run_deepseek_audit.py | Passing CI or an independent acceptance record |

## Acceptance record for a future approved demo

Record the source's rights/confidentiality approval, format, repository commit, provider/configuration category, chosen dictionary version, validators used, reviewer and remaining issues. Do not record API keys, sensitive document text or internal endpoints in a public acceptance record.

Review numbers/units, terminology consistency, missing/untranslated text and visual output. For CAD, verify labels and placement alongside unchanged geometry. For PDF/DOCX/Excel, compare page/sheet/table structure with the source. A reviewer decides whether the output is usable.

Use newly authored synthetic source content for a public demonstration. Previously tracked spreadsheets/exports do not become approved examples merely because they are public.

## Status

The implemented validators and model-assisted checks are distinct from a future regression harness. A reproducible synthetic format matrix, automated test suite and CI gate are **PROPOSED** work; no completion or passing result is claimed.

## Format and fallback limits

Excel/XLS, DOCX, PDF and DXF paths are implemented. Complex scans, non-text objects and CAD overlays require inspection and can need additional OCR/external tooling. PDF text-block reconstruction does not guarantee exact page fidelity; CAD text size/placement may need manual correction.

DWG material should be converted to DXF before import. A separate external-converter helper exists, but direct DWG input is not established in the reviewed UI/batch path.

A provider fallback may retain source text. Residual-source checks and reviewer inspection must distinguish that from a completed translation. The workflow diagram describes review responsibilities, not an enforced pre-export approval gate.

No end-to-end format acceptance, clean-machine installation, dedicated regression suite or GitHub Actions passing result was established by this portfolio preparation. Validators and audit helpers are implemented mechanisms; a reproducible synthetic format matrix and CI harness remain proposed work.

## Configuration and historical credential status

Current reviewed provider configuration uses environment variables. The selected current-code review detected no hard-coded provider key; credential validity and all-history clearance were not established.

Supply configuration through the process environment. [.env.example](../.env.example) documents variable names such as DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, OLLAMA_URL and OLLAMA_MODEL, along with local memory/dictionary paths. Its existence does not guarantee automatic environment-file loading. Never put real values in examples, acceptance records or public output.

**CRED-04 / S05 — DeepSeek: OWNER REVOCATION REQUIRED.**

A historical plaintext key was recorded in config.py, line 1, at initial import bab67c3d41f8e534b7dc56bedf30548164059096 and a later reviewed historical snapshot. Current-tree removal/environment configuration did not remove that exposure from history.

Provider-side revocation is unconfirmed. Confirm the affected key was revoked, with a finding identifier and completion date, without supplying the value. This portfolio work did not access provider accounts, test the credential, rotate it or rewrite history.

## Source rights, confidentiality and provider processing

Before a professional run or public example, confirm source ownership, confidentiality, permission for external-provider processing, glossary provenance and permitted publication of the output. A local provider option alone does not certify a private/offline deployment or settle these rights.

Term recommendations and standards-reference dictionaries assist review; they do not establish engineering correctness or automatic regulatory/standards compliance.

The following classifications carry forward the accepted sample review. No file was removed or altered:

| Tracked file | Classification | Basis / required action |
| --- | --- | --- |
| translate.xlsx | **OWNER RIGHTS CONFIRMATION REQUIRED** | Bilingual workbook with document/translation content. Pattern screening cannot establish confidentiality or reuse rights; approve/redact content and metadata before featuring. |
| translate1.xlsx | **OWNER RIGHTS CONFIRMATION REQUIRED** | Chinese-text workbook. Content provenance and rights are unverified; core metadata fields need derivative review. |
| 2026-04-11T18-54_export.csv | **REMOVE/REDACT RECOMMENDED** | Historical export with source/translated text and uncertain provenance. Exclude from portfolio examples; propose a synthetic replacement after approval, without deleting it now. |
| dictionary/approved_terms_seed.csv | **OWNER RIGHTS CONFIRMATION REQUIRED** | Domain terminology and standards-reference seed. Confirm its sources, attribution and permission; no automatic compliance claim. |
| dictionary/candidates_template.csv | **SAFE DEMO** | Verified header-only CSV template, zero data rows. Describes a schema without a document corpus. |
| dictionary/section_terms_seed.json | **OWNER RIGHTS CONFIRMATION REQUIRED** | Related JSON terminology content included for completeness; glossary provenance still requires confirmation. |
| dictionary/translation_memory.json | **SAFE DEMO** | Verified empty JSON object, zero memory entries at the reviewed commit. Future populated memory requires a new review. |


No tracked PDF, DOCX, DXF, DWG or image sample was found in the reviewed default-branch inventory. Limited XML/pattern screening of the two workbooks found no provider-key/email, external-link or macro finding; this does not establish confidentiality or reuse rights. Author/modifier metadata requires review in any approved derivative.

A public demonstration should use newly authored synthetic source material. The export's removal/redaction is a recommendation requiring a separate exact-file decision, not an action included in this documentation package.

## Licensing

No root license was identified at the reviewed snapshot. The owner must decide which code and public documentation they have rights to license. Source documents, dictionaries and third-party terminology require separate provenance and permission decisions; a new code license would not resolve them.

## Review scope

This guide preserves the accepted Phase 2B facts. No application tests, translation run, runtime/configuration change, sample removal, provider incident response or expanded security clearance is performed by writing it.
