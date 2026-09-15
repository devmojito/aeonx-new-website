# CloudFront changes for aeonx.digital

Distribution `E3OYGVP63K0FQS`. Four changes, all in the CloudFront console. None of them
touch the site files, which are already deployed.

## 1. Viewer-request function

Create a CloudFront Function (runtime `cloudfront-js-2.0`) from `viewer-request.js`,
publish it, and associate it with the **default behaviour** as the **viewer request**
function, replacing the function already there.

It redirects `www.aeonx.digital` to `aeonx.digital`, turns the 52 old and alias URLs
into 301 redirects, and keeps the `/folder/` to `/folder/index.html` rewrite the site
needs today. It skips `/api/`, `/manage/`, `/admin/` and `/static/`.

Regenerate and test with `python3 _cfn.py` whenever the redirect list changes.

## 2. Custom error responses

| Origin error | Response page | Response code | Error caching TTL |
|---|---|---|---|
| 403 | `/404.html` | 404 | 60 |
| 404 | `/404.html` | 404 | 60 |

S3 answers a missing file with 403, which is why both are needed.

## 3. Response headers policy

Attach the AWS managed policy **SecurityHeadersPolicy** to the default behaviour. It adds
HSTS, `X-Content-Type-Options`, `X-Frame-Options: SAMEORIGIN`, `Referrer-Policy` and
`X-XSS-Protection`.

## 4. Cache policy

The site files now carry their own `Cache-Control`. The default behaviour's cache policy
should honour origin headers, which the managed **CachingOptimized** policy does.
