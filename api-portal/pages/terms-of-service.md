# Terms of Service

**Effective Date:** January 1, 2026

By accessing the Bookstore APIs, you agree to the following terms:

## Acceptable Use

- Use the APIs only for their intended purpose
- Do not exceed your rate limit tier
- Do not share API keys across applications
- Do not scrape or cache bulk catalog data without authorization

## Rate Limits

| Tier | Limit | Description |
|------|-------|-------------|
| Standard | 100 req/min | Default for all applications |
| Premium | 1000 req/min | Available to approved partners |

Exceeding your rate limit returns `429 Too Many Requests` with a `Retry-After` header.

## Data Privacy

All personal data transmitted through our APIs is subject to our Privacy Policy. You are responsible for handling user data in compliance with applicable regulations (GDPR, CCPA, etc.).

## SLA

We target 99.9% uptime for all production APIs. Scheduled maintenance windows are announced 48 hours in advance via the Changelog.

## API Key Security

- Keep your API keys confidential
- Rotate keys regularly
- Do not embed keys in client-side code or public repositories
- Report compromised keys immediately to api-support@bookstore.example.com

## Changes to Terms

We may update these terms at any time. Continued use of the APIs constitutes acceptance of the updated terms. Material changes will be announced on the Developer Portal.
