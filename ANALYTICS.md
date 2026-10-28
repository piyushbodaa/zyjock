# Opt-in page analytics

This is a basic-consent GA4 integration. No Google script, analytics cookie, consent ping,
or event is sent until the visitor explicitly opts in. Declining is equally available;
Analytics settings allows withdrawal. GPC and DNT override stored consent. Consent is
stored locally under `site-analytics-consent:v1`; analytics cookies are host-only, prefixed
`site_analytics`, and removed on withdrawal. Application data/storage is untouched.

The production hostname is an exact HTTPS allowlist. Previews, localhost, and unknown
paths are excluded. Only fixed public route/title values are used; dynamic entries are
grouped. Queries, hashes, referrers, typed responses, form fields, personal records, and
user IDs are not sent. This code emits only `page_view`. GA4 can also generate basic
session/engagement events; those use the same sanitized context. No custom interaction
events are registered. History/progress/private routes are not measured.

## Required before production publication

- Verify the measurement ID belongs to this canonical site.
- Keep **all Enhanced Measurement off**, including automatic history pageviews, form,
  site search, outbound link, download, scroll and video events. `send_page_view: false`
  alone does not disable stream-side automatic history events.
- Verify Google Signals, user-provided data and advertising personalization are off.
  The code also denies all advertising consent and disables Google Signals/personalization.
- Review the property's granular location/device settings with the owner.
- On a preview, confirm no Google request occurs even with stored consent.
- After authorized publication only, verify the live default/denied/accepted/withdrawn
  paths, sanitized collection payload, one pageview per route, and Realtime ingestion.
- Test query/fragment-only changes and Back/Forward: no duplicate views or private values.

Run `node --test tests/analytics.test.mjs` for dependency-free browser-contract tests.
These tests intentionally stub Google and do not send real analytics traffic.

References: [Google pageviews](https://developers.google.com/analytics/devguides/collection/ga4/views),
[basic consent](https://developers.google.com/tag-platform/security/guides/consent),
[configuration](https://developers.google.com/analytics/devguides/collection/ga4/reference/config).
