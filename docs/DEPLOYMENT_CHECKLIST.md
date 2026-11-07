# Not-ready-for-public-deployment checklist

Before connecting real students:

- SSO/OIDC and enforced RBAC, password reset, MFA for professors
- Institutional GDPR lawful basis, processor agreements, DPIA, retention schedule, data subject rights
- Consent collection with timestamps/version and specific processing purposes
- Audited anonymization and aggregate thresholds resistant to linkage and inference
- Encryption at rest, field-level encryption as appropriate, secrets manager and private storage
- Production database with backups and access logging (without student chats in logs)
- Verified restrictions on model-provider training, residency and external subprocessors
- Recording notices and authorization for audio/camera/whiteboard capture
- Student accessibility profile must remain private and never influence grades or selection
- Teacher review and human ownership of summative grading
- Separate voluntary research/career portfolio export; no automatic candidate ranking
- Real-time capture and synchronization design if required
