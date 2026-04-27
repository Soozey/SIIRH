# Inspection Workflow Tests

## Target Flows

1. Employee complaint -> inspector qualification -> employer response -> tracked closure
2. Confidential harassment report with restricted visibility
3. Inspector request for documents with due date and reminder
4. Employer submission of compliance proof
5. History export showing all status changes and messages

## Assertions

- only allowed actors can see or reply
- message history is ordered and immutable
- attachments are access-controlled
- deadlines generate alerts
- confidential cases are not visible to unauthorized employer users
- audit log records all reads and writes on sensitive cases
