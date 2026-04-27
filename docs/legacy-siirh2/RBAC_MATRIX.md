# RBAC Matrix

| Role | Payroll | Workers | Contracts | Inspection | Alerts | Admin |
| --- | --- | --- | --- | --- | --- | --- |
| Admin | full | full | full | full | full | full |
| RH | read/write | read/write | read/write | read/write limited by tenant | read | none |
| Comptable | read/write payroll inputs and outputs | read | read | none | read payroll alerts | none |
| Employeur | read company payroll outputs | read company employees | read/write company responses | respond on company cases only | read company alerts | none |
| Manager | team read | team read | limited | none by default | read team alerts | none |
| Employe | own payslips | own dossier | own contract docs | create/follow own cases | read own alerts | none |
| Inspecteur | no payroll internals by default | limited to case context | limited to case context | full inspection workflow | read inspection alerts | none |
| Audit | read-only | read-only | read-only | read-only confidential by policy | read-only | none |
