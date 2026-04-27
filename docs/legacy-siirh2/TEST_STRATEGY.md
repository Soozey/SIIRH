# Test Strategy

## Objectives

- preserve payroll behavior
- validate sensitive workflow permissions
- validate inspection exchanges
- validate data integrity between RH and payroll

## Test Layers

### Unit

- payroll helpers
- formula evaluation
- contribution calculations
- alert rule evaluation
- inspection status transitions

### Integration

- payroll preview endpoints
- payroll import endpoints
- reporting endpoints
- RBAC-protected routes
- inspection case creation and messaging

### Database integrity

- uniqueness of payroll rows
- employee/contract/assignment consistency
- attachment ownership
- alert deduplication

### UI and workflow

- payroll critical forms
- leave/absence entry
- inspection complaint and response flow
- role-specific navigation and visibility

## Initial Guardrails Added

- `siirh-backend/test_payroll_guardrails.py`
