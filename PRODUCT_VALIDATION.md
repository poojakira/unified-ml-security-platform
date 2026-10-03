# Product Validation

## Product boundary
Integration/control-plane layer for the AI-security product family. Individual scanners and evaluators remain separate evidence-producing engines.

## Real-world validation ladder
1. Product health and security-contract tests.
2. Cross-service authentication and finding-schema compatibility.
3. Pin each child product to a concrete revision for release validation.
4. End-to-end request path across at least two real child services.
5. External pilot with a real ML/agent workflow before any production-readiness claim.

## Evidence rules
Stub health endpoints are not product validation. A platform release must record which child revisions were exercised.
