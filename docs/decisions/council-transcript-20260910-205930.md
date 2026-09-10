# Council Transcript — Whole-Project Review

**Project:** AI Recruiter Agent
**Counciled:** 2026-09-10
**Format:** 5 advisors (independent) → 5 anonymized peer reviews → chairman synthesis

---

## The framed question

Judge the AI Recruiter Agent as it stands today and identify bottlenecks, security threats,
improvements, unnecessary work, and architecture problems — in plain language.

**What it is:** a zero-recurring-cost web app (FastAPI backend + React/Vite SPA + Supabase).
A recruiter ("Owner") describes a hiring need in plain English; an AI agent runs the pipeline
— requirement parsing → form generation → distribution → response monitoring → interview
invites → **live AI voice interview** → scorecard — up to but *not* including the hire/reject
decision, which a human always makes. Candidate PII falls under the EU AI Act (recruitment =
high-risk) and India's DPDP Act.

**Built:** LLM Router (free-tier Gemini→Groq per-provider model chains; pauses all AI work,
emails the Owner once, and auto-resumes at the next quota reset when every free tier is
exhausted — never calls a paid model); 5 connectors (Supabase, LLM Router, Speech-to-Text,
Email/Brevo, Zoom); 2 agents (Requirement Parser, Form Builder); Owner auth (Supabase Auth +
mandatory TOTP MFA + backend JWKS verification requiring `aal2`); 17-table Postgres schema
with RLS as a *second* isolation layer (the backend uses the service-role key, which bypasses
RLS, so every endpoint must *also* filter by `owner_id` in code); Owner Console UI; 74 tests.

**Not built:** distribution, response monitoring, notifications, meeting creation, the **live
AI voice interview** (the largest phase — a custom Playwright/Chromium bot joins Zoom/Meet and
uses Chrome's Web Speech APIs for STT/TTS, wired through OS-level virtual audio routing on a
free Oracle Cloud VM; flagged as the highest-uncertainty item), scoring, the decision screen,
and persistence (requisitions/forms aren't saved yet).

---

## Anonymization map (revealed)

| Letter | Advisor |
|---|---|
| A | The First Principles Thinker |
| B | The Expansionist |
| C | The Executor |
| D | The Contrarian |
| E | The Outsider |

---

## Advisor responses

### A — The First Principles Thinker

Almost none of the build touches the real job: less recruiter time spent on mechanical work.
The live-voice-interview goal is a framing error. What the recruiter actually needs is a
*reliable signal* about a candidate. A voice bot screen-scraping Google Meet through virtual
audio cables is the most fragile, most regulated, most gameable way to get that signal.
Asynchronous screening — the candidate records answers to set questions, you transcribe and
score them — produces the same signal with a fraction of the technical and regulatory risk.
"Zero cost" is the wrong north star: the quota-pause machinery, the keep-alive cron, the
five-model chains are all elaborate taxes paid to dodge a ~$20/month bill. A rebuilt v1:
skip the live interview entirely — form → distribute → async recorded screening →
transcript + scorecard → human decides. Ship that, get one real hire through it, *then*
decide whether a live bot is worth the trouble.

### B — The Expansionist

The LLM Router is the crown jewel and it's buried as plumbing. Extract it as a standalone
open-source library plus a hosted "AI reliability router" — provider fallback, quota-aware
routing, and graceful degradation are a real, unsolved pain for anyone building on free or
cheap LLM tiers. Multilingual Hindi/Marathi voice interviewing is a genuine moat: English-first
interview bots can't serve the 500M+ vernacular Indian workforce. The wedge is vernacular-first
hiring for Bharat, with Apna / WorkIndia / Vahan as distribution channels or eventual
acquirers. Compliance-by-design, done properly, is itself a sellable artifact. Position for
this now: instrument every LLM call, routing decision, and scorecard into an event log;
namespace the agents so they're pluggable; move the router into its own repo; and treat the
transcript store as the eventual product, not a byproduct.

### C — The Executor

Rough timing for one person: Phase 2 (distribution + monitoring) — weeks. Phase 3
(notifications) — days. Phase 4 (meeting creation, Zoom only, skip Meet) — weeks. Phase 5
(live interview) — *months*. Phase 6 (scoring + decision screen) — weeks. The virtual-audio
bot on a free Oracle VM is a rabbit hole: PulseAudio null sinks + Playwright + headless
Chrome + Zoom's bot detection + WebRTC timing, all on a 1-OCPU / 1GB ARM instance. Chrome's
Web Speech API is undocumented for server-side use and has no SLA. Zoom actively fights bots.
Expect 6–8 weeks before you even know if it works. Don't build the media pipeline from
scratch — use Zoom's Meeting SDK, or LiveKit Agents / Pipecat, and run the interview in your
*own* WebRTC room where you control the audio. Highest-leverage move right now: a timeboxed
two-week Phase 5 voice spike, *before* Phases 2–4, ending in a hard go/no-go.

### D — The Contrarian

The fatal flaw: the whole edifice rests on abusing free tiers to run a legally high-risk
workload. The LLM Router is a single point of daily failure with no floor under it —
"auto-resumes at quota reset" is not the human oversight the EU AI Act requires; it's an
outage dressed up as a feature. The service-role key living in the app tier is a PII breach
waiting to happen: "filter by `owner_id` in every endpoint" is a promise to never make a
mistake across dozens of handlers, and one missing `.eq("owner_id")` exposes the entire
candidate database across tenants. RLS *was* the actual defense, and it was deliberately
bypassed. Use per-request, JWT-scoped database connections and keep RLS live. Meanwhile the
project is over-built for its stage: mandatory MFA, 17 tables, a 5-model chain, and a
three-cloud deployment for zero users and no persistence. Zero-cost is a liability that is
actively forcing bad architecture — the shared key and the quota-pause both vanish the moment
you accept a ~$20/month bill.

### E — The Outsider

Picture the actual moment: a nervous candidate who needs the job is talking to a robot that
decides whether they advance — in Hindi or Marathi, through a browser speech engine tuned for
English. The off-script answers, the accents, the bad connections, the thinking pauses — that
is exactly where it breaks, and those are the moments that matter. The whole thing is
backwards: the builder has finished the safe, easy 20% and left the risky core unbuilt while
already committing to it in the README. The fact that the audio plumbing is described as the
"hardest, least-certain" piece is a warning that the product may simply not be feasible as
described. "$0/month forever" openly conflicts with the ambition. This is almost certainly a
high-risk AI system that needs human-oversight documentation, bias audits, candidate
notifications, and a DPIA — a serious compliance load for one person. And hand-reimplementing
database protection in every single query works right up until the one time someone forgets.

---

## Peer reviews (anonymized advisors A–E)

### Peer review 1

Strongest: **C** — the only response that turns the problem into a schedule and a concrete
build decision (own WebRTC room instead of scraping Meet). Biggest blind spot: **B** — it
scales a project that can't yet get one candidate through the pipeline, and an event log of
routing decisions and scorecards for a high-risk system is discoverable evidence with no
compliance process behind it. What all five missed: whether a solo, unpaid builder can
*lawfully operate* a high-risk EU AI Act system at all — the provider obligations
(documentation, conformity assessment, post-market monitoring) attach regardless of
architecture, and async screening doesn't escape them.

### Peer review 2

Strongest: **C** — actionable, correctly ranks Phase 5 as the existential risk, kills the
Meet integration. Biggest blind spot: **B**. What all five missed: "a human always makes the
final decision" does *not* remove the high-risk classification — AI that screens, ranks, or
filters who reaches a human is itself high-risk under the Act. Also: nobody has validated that
mechanical screening is actually this recruiter's bottleneck.

### Peer review 3

Strongest: **D** — names the two load-bearing architectural failures concretely (service-role
key makes RLS decorative; quota-pause is not human oversight) and ties them to the zero-cost
constraint. Best *constructive* response: **C** (the own-room insight dissolves the OS-audio
problem). Biggest blind spot: **B** — treats a legally high-risk, zero-user, half-built
project as a platform play. What all five missed: whether a solo builder should ship a
high-risk recruitment system at all — DPIA, bias auditing, logging, post-market monitoring,
personal liability, candidate right-to-explanation. Also: candidate consent/dropout economics,
and whether the AI screening signal actually predicts job performance.

### Peer review 4

Strongest: **D** — lands the only defect that is both concrete and current (tenant isolation
rests on never omitting `.eq("owner_id")`), ties it to the regulatory frame, and gives a fix.
**C** is the best builder's answer if the live interview survives. Biggest blind spot: **B** —
there is no product yet; instrumenting an event log for a high-risk system with no compliance
process behind it creates discoverable evidence. What all five missed: nobody asks what the
recruiter actually does today, or whether a single real person has agreed to use this — no
design partner, no validated bottleneck. Also: candidate-side consent/appeal, and that a solo
builder cannot be the "human oversight" the Act requires for their own automated system.

### Peer review 5

Strongest: **D** — the only response naming mechanical failure modes with specifics, and it
correctly reframes zero-cost as the root cause forcing the shared key and the quota-pause.
Biggest blind spot: **B** — a growth memo for a thing that can't safely run once. What all
five missed: whether a solo builder should ship a high-risk EU AI Act recruitment system at
all — the DPIA, conformity assessment, bias audit, logging, and post-market monitoring are a
compliance *program*, not a checklist item; personal liability plus real candidate harm argue
for staying a decision-support tool with a human at every gate, or not shipping in the EU.

---

## Chairman's synthesis

### Where the Council Agrees

1. **Phase 5 (the live AI voice interview) is the whole ballgame, and it is the riskiest
   possible way to build it.** Four of five advisors (A, C, D, E) independently said the
   custom Playwright + virtual-audio-routing bot on a free Oracle VM is likely infeasible as
   described. The build so far is the safe, easy part; the part that's been committed to
   publicly is unbuilt and unproven.

2. **The service-role key in the backend is a real, present security hole.** The backend
   bypasses RLS and re-implements tenant isolation as "remember to filter by `owner_id` in
   every handler." One omission exposes every candidate's PII across every recruiter account.
   This was the single most-praised point in peer review (strongest response, 3 of 5 votes).

3. **"Zero recurring cost" has become a liability, not a virtue.** The quota-pause machinery,
   the five-model chains, the keep-alive cron, and the shared service-role key all exist to
   avoid a bill of roughly $20/month. Multiple advisors called this out as the root cause of
   the architecture problems.

4. **Nobody has validated the premise.** No design partner, no named real role to hire for,
   no evidence that mechanical screening (rather than sourcing, or judgment) is the actual
   bottleneck for the target user.

5. **B's "turn it into a platform" framing is premature.** All five peer reviews named B as
   the biggest blind spot. There is no product yet; scaling talk is a distraction.

### Where the Council Clashes

- **Async screening vs. live interview (A vs. C).** A says drop the live interview entirely —
  async recorded answers give the same candidate signal with far less risk. C says if the
  live interview stays, build it in your own WebRTC room (LiveKit/Pipecat/Zoom Meeting SDK),
  never by scraping Meet. These aren't fully opposed: do the two-week spike C recommends, and
  if it's a no-go, fall back to A's async design.

- **Is the LLM Router an asset or a liability? (B vs. D).** B calls it the crown jewel worth
  extracting as its own product. D calls it a single point of daily failure with no floor.
  Both are right about different things: the *engineering* is genuinely good and reusable; the
  *dependency on it as the only inference path for a high-risk system* is fragile.

- **How much of the current build is over-engineering (D vs. everyone).** D says mandatory
  MFA, 17 tables, and the multi-cloud plan are premature for zero users. The others don't
  push back hard, but the counter-view is that the schema and auth are cheap to keep and
  costly to retrofit.

### Blind Spots the Council Caught (in peer review)

- **The legal one, raised by all five reviews:** a human making the final call does **not**
  remove the EU AI Act high-risk classification. AI that screens, ranks, or filters who
  reaches a human is *itself* high-risk. The provider obligations — DPIA, conformity
  assessment, bias/accuracy testing, technical documentation, logging, post-market monitoring,
  registration — attach to the operator regardless of architecture, and they are a sustained
  compliance program, not a checklist. For a solo unpaid builder this is likely the binding
  constraint on the entire project.

- **A solo builder cannot be the "human oversight" for their own automated system** in any
  meaningful sense — the person who built the pipeline rubber-stamping its output is not
  independent review.

- **Candidate-side mechanics are entirely absent:** consent that meets DPDP/GDPR standards,
  the right to an explanation, an appeal path, and the dropout economics of asking nervous
  candidates to talk to a bot.

- **Nobody has checked that the AI screening signal predicts job performance.** If it doesn't,
  the whole pipeline is faster delivery of a worse decision.

### The Recommendation

**Stop building forward. Do three things, in this order:**

1. **Two-week timeboxed Phase 5 voice spike, now, before Phases 2–4.** Prove or kill the live
   interview. Build it in your own WebRTC room (LiveKit Agents or Pipecat), not by joining
   Meet through virtual audio. Hard go/no-go at day 14. If no-go, adopt A's async recorded-
   screening design — it reaches a shippable product far sooner.

2. **Close the PII hole regardless of what else happens.** Switch the backend to per-request,
   JWT-scoped Supabase connections so RLS is the *live* enforcement layer, not a dormant
   second copy of rules you also hand-maintain in Python. This is the one change that can't wait.

3. **Get a written answer on the EU AI Act question before writing more agent code.** Either
   (a) scope the product to decision-support with a genuine independent human at every gate
   and take legal advice on whether that still triggers full high-risk obligations, or
   (b) exclude the EU at launch and serve India only, where the DPDP timeline gives you room,
   or (c) accept that the compliance program is part of the build and plan for it explicitly.
   Also: line up one real recruiter with one real open role as a design partner before Phase 2.

**On zero-cost:** keep it as a *default*, not a *constraint*. Let the architecture assume a
small paid tier is available for the parts where free tiers force bad design (inference floor,
managed auth, a real VM for the voice pipeline), and note where you're choosing to stay free.

**Keep:** the LLM Router (it's good work — just don't let it be the only inference path), the
Supabase schema, the Owner auth. **Don't extract the router as a product yet** — there's no
product to extract it from.

### The One Thing to Do First

Run the two-week voice spike in your own WebRTC room (LiveKit or Pipecat), starting now,
ending in a written go/no-go. Everything downstream — the schedule, the async fallback, the
compliance scope, whether this is even the right product — depends on that answer, and you
don't have it yet.
