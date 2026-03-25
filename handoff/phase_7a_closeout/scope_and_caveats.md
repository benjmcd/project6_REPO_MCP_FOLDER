# Scope and Caveats

## Proven
- **Advanced OCR (PaddleOCR)**: Functional and high-signal on NRC ADAMS documents. Successfully handles various layouts.
- **Advanced Table (Camelot)**: Effectively extracts borderless tables. Proven on Technical Specification Amendments.
- **Advanced Execution**: Verified on 43-file corpus; scale behavior for 1000+ files remains unvalidated.

## Partially Proven
- **Larger-Scale Behavior**: Not yet empirically validated.
- **Environmental Portability**: Success depends strictly on the provisioned Python 3.11 / Paddle / Ghostscript stack.

## Out of Scope
- **Post-Extraction Downstream Analysis**: The actual use of these tables in LLM workflows is the subject of the next milestone.
- **Automated Environment Provisioning**: Standardized containerization of the Paddle/Ghostscript stack was not part of this slice.
