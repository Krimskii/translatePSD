# translatePSD

**Chinese-to-Russian translation for technical documentation, with terminology, document structure and human review built into the workflow.**

Technical documents are difficult to translate because terminology, numbers, drawings, tables and layout must survive the process. A fluent sentence is insufficient if a unit changes, a label moves or a table loses its meaning.

translatePSD combines document/CAD processing with dictionaries, translation memory, model routing and validation to support that engineering problem.

## What I built

- Extraction and reconstructed output for Excel, DOCX, PDF and DXF.
- Discipline-specific terminology dictionaries and a separate candidate/approval workflow.
- Persistent, section-aware translation memory and repeated-text deduplication.
- Ollama/DeepSeek routing and fallback paths for unresolved text.
- Terminology/rule validators, residual-Chinese checks, normalization, review flags and optional LLM quality review.
- A Streamlit interface with multi-file/folder processing and ZIP/status output.

## How it works

**Document/CAD input → extraction → terminology/dictionary → translation memory → model routing → translation → validators → human acceptance → reconstructed output**

The sequence expresses the review workflow rather than an enforced execution order. Reconstructed exports are inspected against the source before final human acceptance.

Dictionary and memory lookups resolve known text before model routing. Validators and optional model-assisted checks surface issues for review. If a provider is unavailable, a fallback may retain source text; that still requires translation.

## Supported formats

| Input | Implemented workflow | What the reviewer checks |
| --- | --- | --- |
| Excel / XLS | Cell translation and XLSX output | Sheets, numbers, formulas and terminology |
| DOCX | Paragraph/table processing and reconstruction | Formatting, tables and non-text objects |
| PDF | Text-block extraction/reconstruction, with OCR paths | OCR errors, tables and text placement |
| DXF | Drawing text/block processing, with OCR overlay paths | Labels, symbols, size/placement and unchanged geometry |
| DWG source | Convert to DXF before import | Direct DWG import is not established in the current UI/batch path |

Complex scans and CAD overlays can need manual correction and additional tooling. PDF reconstruction aims to preserve text-block placement rather than guarantee exact page reproduction. Professional output requires human acceptance.

## My role and development approach

I define the product workflow, requirements, acceptance criteria and delivery boundaries. AI coding assistance supports bounded implementation; verification, cross-review and human acceptance remain part of delivery.

The implemented validators support document review. A dedicated automated regression suite and CI gate are proposed next steps.

## Technology

Python · Streamlit · pandas/openpyxl · python-docx · PyMuPDF · ezdxf · OCR integrations · Ollama · optional DeepSeek

Terminology and memory use local CSV/XLSX/JSON workflows.

## Local setup

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Supply configuration through the process environment using the variable names in [.env.example](.env.example). OCR and external CAD tooling can require additional installation.

Existing DXF entry point:

```powershell
python run_dxf.py input.dxf output.dxf
```

## Documentation and acceptance

- [Dictionary workflow](dictionary/README.md)
- [Quality and acceptance](docs/QUALITY_AND_ACCEPTANCE.md): review criteria, format limits, sample/dictionary rights, provider configuration and historical credential status

Use approved, non-sensitive source material. The acceptance guide records provider-processing permissions, tracked-sample provenance and licensing status; tracked samples are not pre-approved portfolio examples.
