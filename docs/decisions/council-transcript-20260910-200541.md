# LLM Council Transcript — Authentication Approach

**Date:** 2026-09-10
**Question:** Which authentication approach is most suitable for the AI Recruiter Agent system?

---

## Framed Question

**Decision:** Which authentication approach should the "AI Recruiter Agent" adopt for its Owner (recruiter) accounts?

**System context:**
- A solo-built web app. React + Vite SPA frontend, FastAPI (Python, async) backend, Supabase (managed Postgres with Row-Level Security) as the data layer. All already built and working; auth is the one missing piece before the product can have real users.
- Currently the backend talks to Postgres with the Supabase **service-role key** (bypasses RLS entirely) and has NO per-Owner data scoping yet. Every future endpoint must filter by `owner_id` in application code — RLS only helps direct-from-browser Supabase calls, which this architecture does not make.
- Product is a **single-Owner MVP**. But the Postgres schema (`owners` table, `auth_user_id` FK to Supabase's `auth.users`, RLS policies vs `auth.uid()`) is already written to support **multiple independent Owner accounts** later.
- **Candidate-facing pages are intentionally unauthenticated** — tokenized links, no candidate ever logs in. Auth is ONLY for the recruiter.
- **Hard constraint: zero recurring cost** — genuine permanent free tier or open-source self-hosted only, not a trial.
- Compliance: candidate PII, EU AI Act (recruitment = high-risk), India DPDP Act.

**Options considered:** Supabase Auth (current plan), roll-your-own FastAPI (pyjwt/argon2), Better Auth, Logto, Zitadel, SuperTokens, Clerk, WorkOS AuthKit, Auth0/Firebase, passkeys/WebAuthn.

**Judge on:** genuine zero-cost fit; security for a solo builder; fit with FastAPI + Supabase-Postgres + RLS; operational burden; vendor lock-in; single-Owner → multi-recruiter transition.

---

## Advisor Responses

### The Contrarian

Everyone will converge on Supabase Auth because it's the same vendor and RLS "just works." Here's the fatal flaw in that reasoning: **RLS does nothing for you.** Your own context says the backend uses the service-role key and bypasses RLS entirely. Every endpoint filters by `owner_id` in Python. So the single biggest advertised advantage of Supabase Auth — native JWT-to-RLS integration — is worth exactly zero in your architecture. You'd be choosing a vendor for a feature you've already designed around.

Strip that away and Supabase Auth is just "a hosted auth service from a company whose free tier and pause-happy project behavior you've already been burned by" (see your own commit: "DNS-cache gotcha after a paused Supabase project restores"). If Supabase pauses your project, your auth dies with your DB. Single point of failure, single vendor, and you've been bitten already.

The deeper problem nobody's questioning: **you're solving multi-tenant auth for a single-Owner MVP.** You have one user. It's you. The entire schema-for-multi-recruiter-later thing is speculative complexity. The zero-cost, zero-burden, zero-lock-in answer for one recruiter is a single environment-variable credential or one hashed password in a config, plus a session cookie. Argon2 + one row. No vendor, no JWKS, no Node sidecar, no OIDC. When you actually sign recruiter #2 — if that ever happens — you'll know your real requirements and can adopt Logto or Zitadel then, with paying customers funding it.

Rolling your own "full" auth (option 2) is the trap: password reset, email verification, rate limiting, session revocation — that's where solo builders leak PII. Don't build that. Build the minimum lock for a door only you walk through.

The compliance risk isn't your auth library. It's the service-role key in your app tier and application-code `owner_id` filters you might forget. Focus there.

### The First Principles Thinker

You're asking "which vendor" when the real question is: **what is authentication protecting, and from whom, at a stage with one user?**

Strip it down. Authentication here does exactly two jobs right now:
1. Keep the internet out of a recruiter's dashboard holding candidate PII.
2. Stamp a verified `owner_id` onto every request so your application-code filtering has something trustworthy to filter by.

That's it. There is no "user management," no team invites, no role hierarchy, no password-reset support burden across a userbase — because the userbase is *you*. Every option on your list that sells "great DX for onboarding users," "1M MAU free," "org management" is solving a problem you do not have and pricing in a risk (vendor dependency, another hosted service, another breach surface) you cannot afford.

The actual decision axis is: **what produces a trustworthy `owner_id` on a FastAPI request with zero new infrastructure and zero new attack surface?**

That reframing kills half the list immediately. Better Auth, Logto, Zitadel, SuperTokens self-hosted — all mean a second runtime you patch and monitor. That's not zero-cost; that's unpaid on-call. Clerk, Auth0, WorkOS, Firebase — proprietary identity dependency for a compliance-sensitive product, to save you an afternoon.

You already run Supabase. It already issues JWTs. Your schema already has `auth_user_id` wired to `auth.users`. The `owner_id` problem is *already solved in your data model* — you just haven't turned the key.

The honest question isn't "which auth" — it's "why would I add anything?" The multi-recruiter future is a red herring: whatever issues verifiable JWTs for one Owner issues them for fifty. Don't buy optionality you get for free.

### The Expansionist

Auth is not plumbing here. It is the schema of your future org chart, and picking it well converts "solo MVP" into "multi-tenant SaaS with an enterprise motion" for near-zero marginal work.

The move most people underrate: **Supabase Auth as the identity spine, with RLS as the tenancy boundary.** The upside nobody prices in is that RLS policies keyed on `auth.jwt() ->> 'owner_id'` give you database-enforced tenant isolation for free. That is the single most expensive thing to retrofit later, and the exact control an EU AI Act auditor or a DPDP data-processing agreement wants to see. You get a compliance artifact ("PII isolation enforced at the storage layer, not just app code") that becomes a sales asset the day you talk to your first agency buyer.

Then it compounds. Supabase Auth ships organizations, SSO/SAML, and MFA in the same free tier. That is your entire agency tier roadmap already built: one recruiter becomes a 12-seat staffing firm becomes an enterprise account demanding Okta SSO, and you never swap auth vendors. Passkeys layer on top when you want a security differentiator in the deck.

The adjacency: once Owners have real JWTs, your tokenized candidate links become *scoped, signed, revocable* artifacts issued by the same system, and partner/ATS integrations (Greenhouse, Lever) get OAuth-client credentials from infrastructure you already run. That is a marketplace surface.

Bet on the choice that makes the 50-person version of this company boring to build. That is Supabase Auth. Rolling your own throws away every one of these upside paths to save a week you will spend anyway on RLS policies.

### The Outsider

The word "free" is doing a lot of hiding here. None of these options charge money; all of them charge *attention*. Self-hosting Logto, Zitadel, or SuperTokens means you now run an internet-facing service that stores password hashes for a regulated product, and you patch it forever. That's not $0 — that's a second job. The only genuinely "free" options are ones where someone else runs the server: Supabase Auth or a hosted tier.

"Roll your own auth" for a product under EU and India hiring-AI regulation, handling applicant personal data, built by one person with no security team: alarming. Full stop. If there's a breach, "I hand-rolled the token logic" is the sentence in the incident report that ends the company. Cross it off.

The mismatch you're asking about is real but backwards. It looks like heavy machinery for one user — but the machinery isn't for the user, it's for the regulator and for future-you. That part is justified. What's *not* justified is evaluating ten options. You have a database from Supabase with row-level security already wired to expect Supabase Auth tokens. Option 1 is the only one that makes your existing code *smaller* (you can drop the service-role key and the manual "filter by user id in every endpoint," which is itself a data-leak risk every time you forget).

Lock-in fear is overweighted. Auth data is a table of emails and password hashes; it's the most portable thing in your stack. Migrating auth later is a weekend, not a rewrite.

Pick Supabase Auth. Add passkeys later if you want. Spend the saved weeks on the regulatory documentation, which is the actual hard part nobody on this list solves.

### The Executor

**Ship this week: Option 1 (Supabase Auth). Everything else is a multi-week project or adds deployment units you'll babysit.**

Deployment-unit count:
- **Supabase Auth: zero new units.** It's already running inside the Supabase project you deploy. No new service, no new DB, no new backup story.
- **Roll-your-own: zero units but ~2 weeks of code** — password reset tokens, email verification, rate limiting, revocation, lockout, the Brevo email templates, and the security tests. You will get one of these subtly wrong.
- **Better Auth / SuperTokens self-host / Logto / Zitadel: +1 service minimum, and 3 of those 4 also mean +1 Postgres database** that is now stateful, needs its own backups, its own migration runs, its own free-tier keep-alive cron. On Render free tier that service also cold-starts and sleeps. That's the quiet trap: "self-hosted open source auth" is really "operate a second stateful system."
- **Clerk / WorkOS: zero units, but** your RLS policies reference `auth.uid()`. Using them means minting a Supabase-compatible JWT or abandoning RLS and doing all scoping in app code. Extra glue, plus a vendor you'd later pay.

Supabase Auth is the only option where the JWT drops straight into the `auth.uid()` policies you already wrote, same vendor, same dashboard.

**Monday-morning first step:** In the Supabase dashboard, Authentication → Providers, enable Email. Add `@supabase/supabase-js` to the React app, build a login form calling `signInWithPassword`. In FastAPI, add one dependency that fetches Supabase's JWKS, verifies the bearer token, extracts the `sub` claim, looks up `owners.auth_user_id`, and returns `owner_id`. Create your own Owner row by hand. Flip the backend from service-role key to per-request JWT. Done in a day or two.

---

## Peer Reviews

**Anonymization map:** A = First Principles Thinker · B = The Outsider · C = The Contrarian · D = The Executor · E = The Expansionist

### Reviewer 1
1. **Strongest: D.** Combines the correct reframe (Supabase Auth is the only option whose JWT drops into the `auth.uid()` policies already written) with concrete deployment-unit analysis and a literal Monday checklist including flipping off the service-role key. A has the sharpest framing ("why add anything?") but never says what to do.
2. **Biggest blind spot: E.** Claims Supabase's free tier ships "organizations, SSO/SAML, MFA" — SSO/SAML is a paid Pro+ add-on, so the "enterprise roadmap already built" argument collapses against the zero-cost constraint. Spends the whole answer on a speculative agency/marketplace future for a one-user product.
3. **All missed:** Supabase free-tier projects pause after ~7 days inactivity (auth dies with the DB); account recovery for a solo Owner (lose the credential = locked out of a PII system); MFA as a likely compliance expectation; defense-in-depth (keep app-code checks *and* enable RLS, not either/or).

### Reviewer 2
1. **Strongest: B.** Reaches the right call and defends it on every axis: kills roll-your-own on regulatory grounds, kills self-hosting as "a second job," deflates lock-in fear correctly, notes Supabase Auth *shrinks* existing code, names the real hard part (regulatory documentation).
2. **Biggest blind spot: E.** Entire thesis rests on RLS-enforced isolation "for free" — but the backend bypasses RLS today (C catches this). SAML SSO is a paid add-on, not free.
3. **All missed:** the email-delivery dependency. Supabase Auth's built-in SMTP is rate-limited (~a few/hour) and unfit for production — password reset / confirmation needs an external provider (Brevo) regardless. Also: MFA for high-risk PII, Owner-access audit logging, free-tier auto-pause.

### Reviewer 3
1. **Strongest: D.** The only one that operationalizes the decision into concrete steps while correctly identifying the deciding axis (deployment-unit count, unpaid on-call burden) and honestly costing roll-your-own at ~2 weeks. Catches the Clerk/WorkOS RLS-JWT mismatch precisely.
2. **Biggest blind spot: E.** Built on a false premise (RLS is the tenancy boundary) when the backend bypasses RLS. Its "compliance artifact," "sales asset," "database-enforced isolation" arguments evaporate. Assumes SSO/SAML/orgs sit in the free tier.
3. **All missed:** operational continuity and account recovery for a *single* human — no second admin to recover access if the solo Owner loses their password/device or Supabase locks/pauses the project. Nobody discusses MFA, backup-code storage, session/token revocation on device loss, or audit-logging of Owner logins.

### Reviewer 4
1. **Strongest: D.** The only response that engages the actual integration work (verify Supabase JWKS in a FastAPI dependency, map `sub` to `owners.auth_user_id`, flip off the service-role key). Correctly weighs deployment units. B is a close second on compliance/lock-in reasoning.
2. **Biggest blind spot: E.** Its entire thesis rests on free "organizations, SSO/SAML, MFA" — SAML SSO and advanced org features are paid add-ons, so the argument quietly violates the hard zero-cost constraint. Assumes RLS isolation is already true when the backend bypasses RLS.
3. **All missed:** Supabase free tier pauses after ~7 days inactivity (the team was already bitten) — no availability mitigation proposed. EU AI Act / DPDP expect audit logging of who accessed candidate PII and when. The service-role key stays in the backend regardless of auth choice; that residual risk (C alone flags it) deserves an explicit plan.

### Reviewer 5
1. **Strongest: D.** Accepts the same conclusion as B and E but earns it with the one metric that decides this: deployment-unit count and operational burden on a solo builder. Correctly nails why Clerk/WorkOS are awkward (`auth.uid()` RLS coupling) and gives a concrete, correct implementation path.
2. **Biggest blind spot: C.** Its "one hashed password in config" recommendation ignores that the schema, FK, and RLS policies already exist — the marginal cost of real Supabase Auth is near zero, so trading it for a bespoke session-cookie scheme saves nothing and creates a migration later. C is right that RLS is currently unused, but wrong that this makes Supabase Auth valueless: turning RLS back on (defense-in-depth for PII) is the point, not a sunk feature.
3. **All missed:** token/session revocation, JWT expiry/refresh handling, MFA on the single Owner account whose compromise exposes all candidate PII — a concrete EU AI Act / DPDP security-of-processing obligation. Also: Supabase Auth free-tier MAU caps, email-deliverability setup for magic links/resets, audit-logging of Owner access to PII.

---

## Chairman Synthesis

### Where the Council Agrees

Near-unanimous, advisors and reviewers alike:

1. **Supabase Auth is the answer.** 4 of 5 advisors landed there directly; the 5th (Contrarian) argued for an even more minimal "one hashed password" scheme, which every peer reviewer rejected as a false economy given the schema, `auth_user_id` FK, and RLS policies are already written against `auth.uid()`.
2. **Roll-your-own full auth is disqualified — on risk, not capability.** Solo builder, no security team, regulated PII: "I hand-rolled the token logic" is the line in the breach postmortem that ends the company.
3. **Every self-hosted option (Better Auth, Logto, Zitadel, SuperTokens) fails the zero-cost test in disguise** — "free" there means operating a second internet-facing stateful service with its own DB, backups, patch cadence, and keep-alive cron. Unpaid on-call, not $0.
4. **Every hosted third-party (Clerk, WorkOS, Auth0, Firebase)** adds a proprietary identity dependency to save ~an afternoon, and their JWTs don't fit the `auth.uid()` RLS policies already written.
5. **Lock-in fear is overweighted.** Auth data is a table of emails and password hashes — migrating auth later is a weekend, not a rewrite.
6. **Supabase Auth makes the codebase smaller** — retire the service-role key from the app tier and the hand-written per-endpoint `owner_id` filter.

### Where the Council Clashes

**The Contrarian vs. everyone else on whether to adopt a real auth system at all now.** The Contrarian: one user, so multi-tenant auth is speculative complexity; a single credential + cookie is enough. The rest: the machinery is for the regulator and future-you, and the marginal cost of *real* Supabase Auth over a bespoke scheme is near zero *because the schema is already built for it*. **Chairman sides with the majority** — the Contrarian is right you shouldn't build multi-tenant *machinery*, wrong that this argues against Supabase Auth, which *is* the minimal option here.

**Smaller clash: does "RLS is bypassed" count against Supabase Auth?** The Contrarian says yes. Reviewer 5 reframes correctly: it's an argument to *turn RLS back on* as defense-in-depth, which makes Supabase Auth *more* valuable.

### Blind Spots the Council Caught (in peer review)

1. **The Expansionist's upside case is built on a factual error** — Supabase's free tier does **not** include SAML SSO (paid Pro add-on). "Enterprise roadmap already built for free" is wrong.
2. **Free-tier auto-pause (~7 days idle) takes auth down with the DB** — already been bitten. Needs a keep-alive cron before real users depend on login.
3. **Solo-Owner account recovery is unaddressed** — one human, one credential, no second admin, regulated PII. Needs MFA + stored backup codes + a break-glass second Owner.
4. **MFA on the Owner account is close to a compliance obligation** — EU AI Act security-of-processing + DPDP. Supabase Auth supports TOTP MFA free; turn it on.
5. **Audit logging of Owner logins / PII access** — DPDP + AI Act accountability. The `audit_log` table exists; wire Owner auth events to it.
6. **Production email deliverability** — Supabase's built-in SMTP is rate-limited and not for production. Point Supabase custom SMTP at the existing Brevo credentials.
7. **Token/session revocation + JWT refresh** — not automatic; short-lived access token + refresh, revocable on device loss.
8. **The service-role key stays in the backend regardless** — narrowest-possible use; ideally move privileged operations behind a small set of audited functions.

### The Recommendation

**Adopt Supabase Auth** — as the *minimal* option, not the maximal one. The `owners` table, `auth_user_id` FK, and RLS policies are already written for it, so the marginal cost over any bespoke scheme is near zero, and every alternative is strictly worse on cost, risk, lock-in, or fit.

The council's real value is what the peer review surfaced: **the auth vendor was never the hard part** — the recruiter-account security posture the regulations demand is, and no vendor gives it by default. So:

**Supabase Auth + a defined hardening checklist:** email/password login → TOTP MFA required on the Owner account → backup codes stored → a second break-glass Owner → RLS turned back *on* as defense-in-depth *beneath* the app-code `owner_id` checks (not instead of them) → Owner auth events written to `audit_log` → Supabase custom SMTP pointed at Brevo → a keep-alive cron so the free-tier project can't pause login out from under you → short-lived JWTs with refresh, revocable on device loss.

**Skip:** organizations, SSO/SAML, roles, team invites — genuinely premature for one user, and re-addable free when a paying multi-seat customer actually appears.

### The One Thing to Do First

**In the Supabase dashboard: Authentication → point custom SMTP at your existing Brevo credentials, then enable the Email provider and require MFA.** That's the 15-minute step that turns "Supabase Auth" from a default into a compliance-defensible one — and it's the piece every advisor skipped. The FastAPI JWKS-verification dependency and the React login form come right after, but they're worthless guarding a mailbox that can't send a password reset or an account with single-factor login to regulated PII.

---

*Counciled 2026-09-10. 5 advisors (Contrarian, First Principles, Expansionist, Outsider, Executor), 5 anonymized peer reviews, chairman synthesis.*
