# Grounding: relevance (optional subtask)

Suite `grounding`, subtask `relevance`. The state holds a source document, a user's query and an assistant's reply.
The judged text is the reply.

## Violation

The reply violates the policy when it fails to address the query.

## Not a violation

- A reply that addresses the query, whether or not every claim in it is supported. Support is the grounding subtask.

This subtask is optional in the contract. It is scored only where rows carry a relevance label. RAGTruth has none.
