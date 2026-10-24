Original requests (T1-T10). free-* = no guidance; recipe-* = the SKILL.md style guide. Near-miss pairs: T1/T2, T3/T4, T5/T6.

T1: hey, in acme-billing (our django 4.2 DRF api under services/billing/) we need to rip out session auth and use JWT so the new mobile app can log in. priya wants refresh tokens with rotation. don't break the admin.
T2: customers on billing.acme.io keep getting logged out after ~5 min even though SESSION_COOKIE_AGE is 2 weeks. started after we moved django behind the new AWS ALB with 3 instances. logs show new sessionid each request sometimes.
T3: our playwright e2e suite for the storefront (next.js 14) passes locally but in github actions ~20% of runs fail with "Timeout 30000ms exceeded waiting for locator('#checkout')". retries make it worse. fix it pls, CI config is .github/workflows/e2e.yml
T4: src/components/CountdownBanner.test.tsx is flaky in jest — sometimes the "shows expired" assertion fails. it uses setInterval and date-fns. Marco said use fake timers but then the test hangs.
T5: we need to move prod db (postgres 12 on RDS, ~800GB) to postgres 16 with at most a few minutes downtime. thinking logical replication? plan + runbook needed by friday.
T6: the orders table in prod (postgres, 300M rows) needs an index on (customer_id, created_at) — last time someone added an index the site went down for 10 minutes due to locks. do it safely
T7: getting "future cannot be sent between threads safely" in crates/ingest/src/worker.rs when I tokio::spawn the handler — it holds a MutexGuard from std::sync across an .await I think. fix without rewriting everything
T8: write a terraform module under infra/modules/static-site that makes a private S3 bucket + CloudFront distribution with OAC, ACM cert in us-east-1, for marketing.acme.io
T9: the java payments-svc pod keeps getting OOMKilled in k8s (limit 1Gi) even though -Xmx is 768m. need to figure out what's eating memory and tune the JVM for containers
T10: convert our internal lib acme-utils from setup.py + setup.cfg to pyproject.toml using hatchling, keep the version from git tags, and get it publishing to pypi from CI with trusted publishing

Variant requests: different instances of the same ten task types, worded differently.

V1: the flutter app team needs token-based login against our drf backend; currently it's cookie sessions. set up simplejwt, access 15m refresh 7d, blacklist on logout.
V2: users complain they're randomly signed out of the django dashboard since we scaled to 2 ec2 boxes behind an elb. sessions are in the db? not sure.
V3: CI keeps going red — playwright tests, 'page.click: Timeout' on the login button, only on GH Actions ubuntu runners, our nextjs app. can't repro locally.
V4: test for useCountdown hook randomly fails; jest.useFakeTimers + await waitFor never resolves
V5: upgrade aurora postgres 11 → 15, can't afford long outage, ~2TB. blue/green or pglogical?
V6: need a new index on events(user_id, ts) on prod postgres, table is huge, can't take writes down
V7: rustc: `std::sync::MutexGuard<'_, State>` cannot be sent between threads safely, inside axum handler with async db call
V8: host our docs site on aws: s3 + cloudfront, terraform please, bucket must not be public, custom domain with https
V9: spring boot container restarts with exit code 137 under load, k8s memory limit 2Gi, heap is fine per metrics
V10: modernize packaging for our python package — move to pyproject (hatch), setuptools_scm-style versioning, release to pypi via github actions OIDC
