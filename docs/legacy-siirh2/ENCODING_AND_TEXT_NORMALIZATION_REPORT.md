# Encoding And Text Normalization Report

Date: 2026-03-19

## Objective
Eliminate user-visible mojibake and lock a UTF-8 clean perimeter around the screens and backend labels currently used in demonstration and recruitment/reporting workflows.

## Corrected Perimeter
- `siirh-frontend/src/pages/Reporting.tsx`
- `siirh-frontend/src/pages/Organization.tsx`
- `siirh-backend/app/routers/reporting.py`
- `siirh-backend/app/routers/workers_import.py`
- `siirh-backend/app/services/recruitment_assistant_service.py`

## Corrections Applied
- Fixed corrupted French labels and accents in reporting metadata.
- Fixed broken labels in reporting filters and exports.
- Fixed broken strings in the recruitment assistant seed library.
- Fixed broken import template wording in worker import.
- Preserved UTF-8 encoding on saved files.

## Guardrails Added
- Test file: `siirh-backend/test_encoding_guardrails.py`
- Forbidden patterns currently blocked in the targeted perimeter:
  - `Ã`
  - `Â`
  - `â€™`
  - `â€œ`
  - `â€`
  - `�`

## Validation Result
- Targeted encoding guardrail tests pass.
- Frontend production build passes.
- Backend OpenAPI generation passes.

## Residual Risk
- The repository still contains legacy comments and secondary strings outside the protected perimeter that deserve a broader normalization sweep.
- The current guardrail intentionally protects the active user-facing perimeter first to avoid risky wide rewrites near payroll-sensitive code.

## Recommendation
- Extend the same guardrail file list incrementally to the rest of the legacy modules after each normalization batch.
- Keep all new content saved as UTF-8 and reject mojibake patterns in CI.
