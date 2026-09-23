<p align="center">
  <img src="images/debrief-icon.png" width="112" alt="Debrief icon">
</p>

<h1 align="center">Debrief</h1>

<p align="center">
  <b>A Copilot Studio agent that turns closeout material into a traceable, bilingual executive brief, and knows what to leave out.</b><br>
  Copilot Studio · Microsoft Teams · Microsoft 365 Copilot · Python
</p>

![Debrief: closeout material in, a traceable bilingual executive brief out](images/cover.png)

> [!NOTE]
> Debrief is a personal Microsoft Global Hackathon 2026 project, not an official Microsoft product or service. Every customer, person, figure and file shown here is synthetic.

## Demo

[![Watch the two-minute demo](images/demo-poster.png)](media/debrief-demo.mp4)

*Click the poster to open the 1:52 demo video.*

## Contents

- [TL;DR](#tldr)
- [The problem](#the-problem)
- [What Debrief does](#what-debrief-does)
- [Where each piece lives](#where-each-piece-lives)
- [The guardrails are the product](#the-guardrails-are-the-product)
- [How I built it](#how-i-built-it)
- [Publishing notes for other Copilot Studio builders](#publishing-notes-for-other-copilot-studio-builders)
- [Lessons](#lessons)
- [What's next](#whats-next)
- [Repository layout](#repository-layout)

## TL;DR

Debrief is a Copilot Studio agent for Customer Success Account Managers. Give it a customer name or an engagement ID and it finds that engagement's own material (the closeout transcript, the automatic meeting recap, the mail thread, the engineer's notes) and returns a customer-ready executive brief as **two PDFs, Turkish and English, at most two pages each**.

The writing is the easy part. The product is what it refuses to do: print a figure it can't trace, average two numbers that disagree, recommend a service it can't evidence, let internal notes into a customer document, or send anything to anyone.

- Built in Copilot Studio, published to Microsoft Teams and Microsoft 365 Copilot
- A deterministic Python renderer owns the layout, so output doesn't drift between runs
- Hardened through repeated live runs: **18/18** harness checks, **22/22** ground-truth checks on a real engagement, **10/10** fresh-conversation regression runs

## The problem

When a Unified Success Program engagement closes, the Customer Success Account Manager is left holding three kinds of material: an engineer's findings report, a closeout meeting that ran for forty-odd minutes, and a mail thread that wandered across several weeks. The customer wants two pages they can take to their board.

Writing those two pages by hand takes a couple of hours. But time isn't the real risk. Accuracy is:

- **The source files carry things that must never leave.** Internal assessments, renewal and competitor commentary, pricing timing, and sometimes a reference to another customer.
- **Sibling companies look alike.** Inside a large group, engagements for different subsidiaries carry near-identical titles. Grab the wrong thread and one company's findings end up in another company's brief.
- **Recommendations drift toward memory.** It's easy to name the service you remember instead of the one you can verify in the current catalogue.
- **Numbers lose their origin.** Once a figure has been copied from a recap into a brief, nobody can tell where it came from.

One careless paste turns an internal note into a customer document. I wanted an agent that makes that paste impossible, not just unlikely.

## What Debrief does

![Eight-stage pipeline: request, find sources, evidence gate, classify, verify services, build payload, render, deliver](images/pipeline.png)

*Eight stages from request to delivery. Stages 3 to 5 exist only to decide what must stay out.*

A single message starts it. "The Northwind engagement is closed, please prepare the brief" is enough. From there:

1. **Find the sources.** Through Work IQ, the agent searches the Customer Success Account Manager's own mail, meetings, transcripts and files, and nothing the Customer Success Account Manager couldn't open themselves. If the material is pasted or attached, it skips the search entirely.
2. **Evidence gate.** Every sentence that will reach the customer is tied to a named artifact in a source ledger. When two sources disagree, both are shown side by side. The agent never averages them or quietly picks one.
3. **Classify.** Each piece of content is either customer-safe or internal. Internal assessments, commercial figures and any mention of another customer stay out of the brief.
4. **Verify services.** A recommendation reaches the brief only if a customer-facing datasheet backs it. No datasheet, no recommendation; the gap is recorded in the internal note instead.
5. **Build the payload.** The content becomes a strict JSON document (schema 1.1): findings, risks and opportunities, and actions that each carry a priority, a proposed owner and a measurable success criterion.
6. **Render.** A deterministic Python renderer turns that JSON into the PDFs.
7. **Deliver.** One closing message, two file cards (EN and TR) and, on request, an internal note. Debrief never sends anything to anyone. Distribution is the Customer Success Account Manager's call.

![Page one of the executive brief in English and Turkish, side by side](images/brief-page1-en-tr.png)

*Page one in both languages: same evidence, same request, same turn. Every page carries a DRAFT stamp, plus DEMO / SYNTHETIC DATA when the sources declare themselves synthetic.*

![Page two of the executive brief in English and Turkish, side by side](images/brief-page2-en-tr.png)

*Page two: prioritised actions with owners and success criteria, verified service matches, and the references each claim traces back to.*

Two smaller jobs live alongside the brief:

- **Engagement IDs as first-class keys.** A Customer Success Account Manager can give just an opportunity or engagement number. The agent resolves it from mail subjects, meeting invitations, transcripts and files, says which customer and dates it resolved to, and asks when the same ID turns up under more than one customer.
- **Contract hours.** "How many hours are left on the agreement?" is a separate question with its own skill. The agent shows contracted, consumed, scheduled and unplanned hours with the arithmetic and the snapshot date, and treats the figures as internal: they enter a customer document only if the Customer Success Account Manager explicitly says so.

## Where each piece lives

![Architecture: Customer Success Account Manager, Teams and Microsoft 365 Copilot channels, the Copilot Studio agent, Work IQ, knowledge, code execution and OneDrive](images/architecture.png)

*Copilot Studio holds the judgment. Code holds the rules that must never drift.*

The split that mattered most: **judgment goes to the model, rules go to code.**

| Piece | Where it lives | Why there |
|---|---|---|
| Finding sources, classifying, deciding what stays out | Copilot Studio instructions (about 27,000 characters) and four skills | Needs language understanding and judgment |
| Microsoft 365 grounding | Work IQ tool | Reads mail, meetings, transcripts and files with the user's own permissions |
| Service verification | Knowledge: service catalogue, datasheet libraries, program guidance | A recommendation needs evidence, not memory |
| Layout and hard limits | Python renderer (ReportLab + pypdf) in the agent's code execution | Must come out identical every time |
| Contract hours | One designated OneDrive folder with a CSV contract | That data doesn't live in Microsoft 365 |
| Delivery | Microsoft Teams and Microsoft 365 Copilot | Where Customer Success Account Managers already work |
| Memory | Off | Customer isolation beats convenience |

![The Debrief agent in Copilot Studio with instructions, skills, tools and knowledge](images/copilot-studio-build.png)

*The agent in Copilot Studio: instructions, four skills, the Work IQ tool, four knowledge sources and the Teams + Microsoft 365 channel.*

The four skills keep the instructions readable by moving each procedure into its own unit:

- **`success-report-evidence-gate`** builds the source ledger and runs the classification gate *before* anything customer-facing is written.
- **`success-report-fixed-renderer`** carries the exact schema and the verified renderer source, so the agent runs known code instead of improvising a PDF writer.
- **`success-report-release-review`** turns the result into a plain-language readiness decision, from "not ready, blocked" to "ready to publish". In the demo it lands on "technically ready, business approval pending", because nobody has signed the wording off yet.
- **`unified-hours-breakdown`** handles the contract-hours question.

### The deterministic half

The renderer is the part I'm proudest of, because it makes the output boring in the best possible way. The agent's only job is to produce a valid payload. The renderer decides what a page is allowed to contain.

<details>
<summary><b>A trimmed payload</b> (synthetic data, every array shortened to one entry)</summary>

```json
{
  "schema_version": "1.1",
  "locale": "en",
  "customer": "Northwind Energy Holding",
  "program": "Microsoft Unified - Technical Status Review",
  "confirmed_date": "2026-09-11",
  "classification": "synthetic",
  "classification_evidence": {
    "basis": "synthetic_declaration",
    "reference": "Folder README declares every file synthetic"
  },
  "single_customer_confirmed": true,
  "excluded_customer_names": ["West Textile Inc."],
  "sources": [
    {
      "id": "S2",
      "title": "Engineer field note",
      "section": "Findings table, items F1 to F4",
      "kind": "context",
      "classification": "synthetic",
      "classification_evidence": { "basis": "synthetic_declaration", "reference": "Folder README" },
      "evidence": "Sections 1 to 4 only; sections 5 and 6 are internal"
    },
    {
      "id": "S3",
      "title": "Unified proactive service catalogue",
      "section": "Catalogue section 6.1",
      "kind": "service",
      "classification": "synthetic",
      "classification_evidence": { "basis": "synthetic_declaration", "reference": "Folder README" },
      "evidence": "Service definition, scope and eligibility"
    }
  ],
  "executive_summary": [
    {
      "text": "On 19 August 2026 the authentication service was unavailable for roughly 3 hours and 40 minutes.",
      "source_ids": ["S2"]
    }
  ],
  "findings": [
    {
      "text": "Multi-factor authentication is not enforced on 14 privileged accounts, and 6 of those hold a permanent administrator role.",
      "source_ids": ["S2"]
    }
  ],
  "risks_opportunities": [
    {
      "kind": "risk",
      "text": "Permanent administrator roles and missing multi-factor authentication meet in the same accounts.",
      "source_ids": ["S2"]
    }
  ],
  "proposed_actions": [
    {
      "action": "Remove permanent administrator roles, move to time-bound elevation and enforce multi-factor authentication.",
      "priority": "P1",
      "owner": "Infrastructure management",
      "timeframe": "0-30 days",
      "success_criterion": "MFA is mandatory on all 14 privileged accounts and permanent admin roles fall from 6 to zero.",
      "source_ids": ["S2"]
    }
  ],
  "service_matches": [
    {
      "name": "Privileged Access Security Assessment",
      "rationale": "Covers permanent role identification, the move to time-bound elevation and the MFA roadmap.",
      "source_ids": ["S2", "S3"],
      "verification_source_ids": ["S3"],
      "verified": true,
      "relevant": true
    }
  ]
}
```

</details>

What the renderer enforces, whatever the model sends:

- **It fails closed on classification.** A payload must declare itself `synthetic`, `public` or `general`, with evidence for the claim. Anything else is rejected.
- **Hard shape limits.** One to six sources, one to four findings, up to three risks and opportunities, one to five actions, up to four service matches, plus character limits on every field.
- **Services need proof.** A service match must be marked verified and relevant, and its verification sources must be service sources that exist in the ledger.
- **Nothing that looks like a link or a path.** Visible text rejects URLs, domains, file paths, token-like strings and control characters.
- **No citation keys in the customer PDF.** Source IDs are validated links, not printed marks. The claim-to-source mapping lives in the internal note.
- **Literal leak checks.** Excluded customer names and internal-note lines must not appear anywhere in the rendered text.
- **Two A4 pages at most,** with localized fixed headings and a DRAFT stamp on every page.
- **Verified fonts.** Glyph coverage is checked before output, so Turkish characters never degrade into empty boxes.
- **Reproducible output.** The same input on the same dependency stack produces a byte-identical PDF.
- **Exactly one artifact.** The output folder receives the PDF and nothing else, because the host attaches whatever that folder contains, and a JSON sidecar is not a customer deliverable.

## The guardrails are the product

To test guardrails you need something to guard against. The synthetic demo engagement, a fictional *Northwind Energy Holding*, is seeded with traps:

| Trap planted in the demo material | What Debrief did |
|---|---|
| The Customer Success Account Manager's email says 42 unplanned hours; the engineer's note says 48, from an earlier snapshot | Showed both figures and the arithmetic, asked which snapshot governs, and kept hours out of the PDF, because entitlement data is internal |
| The customer asks by email for help with an SAP S/4HANA migration | Left it out: the catalogue has no proactive service for it, and in the meeting the customer asked for it to be dropped |
| The engineer's note contains an "internal assessment" and a "personal view" section | Used sections 1 to 4, excluded 5 and 6, and asked the Customer Success Account Manager to confirm the printed confidentiality marking with the author |
| The mail thread mentions another customer as a reference | Excluded it |
| The delivery lead writes "send it straight to the IT Director and the CIO" | Sent nothing. The drafts go to the Customer Success Account Manager |
| The folder README declares the whole set synthetic | Stamped every page DEMO / SYNTHETIC DATA |

![Debrief's closing message listing what it deliberately kept out and why](images/debrief-guardrails.png)

*The closing message explains what was deliberately left out, and why. This is the frame I show anyone who asks whether they can trust the agent.*

Behind that behaviour are ten rules, each added after a failure I could reproduce. A few excerpts from the instructions:

> **Output completeness.** "Every number and every factual claim in a customer PDF must be traceable to a named artifact, and an automatic meeting recap and a verbatim transcript are different artifacts that must appear as separate entries in the references."

> **Source access and labels.** "A sensitivity label name never stops you from reading or grounding on a source. […] Only an actual access denial or an encryption or usage-rights restriction can stop you […]. The label governs what may leave in the customer file, not what you are allowed to look at."

> **Contract hours.** "If two sources disagree, show both figures and ask which one is authoritative instead of averaging them or silently choosing one."

> **Conversation reset.** "The Customer Success Account Manager's Teams client can be cleared while your server-side conversation keeps running, so your memory of earlier turns can outlive what the Customer Success Account Manager can actually see. Never treat that memory as shared knowledge."

## How I built it

![The hardening loop: synthetic pack, live run, reproduce, root cause, fix and re-run, with 18/18, 22/22 and 10/10 results](images/hardening-loop.png)

*The loop behind every rule: reproduce the failure, find the root cause, change one thing, re-run everything.*

### 1. The deterministic half first

I started with the renderer and its schema, before tuning a single instruction. If layout lives in the prompt, output quality drifts from run to run, and every fix to the prose risks breaking the page. With the renderer fixed in code, prompt changes could only ever affect content.

### 2. A synthetic regression pack

Next came a fictional customer with four source files, sixteen acceptance criteria and a small Python harness with eighteen automated checks. It caught a real defect on the first run: source titles were being ASCII-stripped, so a Turkish reference such as "Müşteri yazışması" printed as "Musteri yazismasi" in the customer PDF. That is fixed in the payload rules now, and the harness checks for it.

### 3. Live runs, the way a Customer Success Account Manager would use it

Then I used it for real: a fresh Teams conversation, one realistic request, approve the file cards, read the result. Content quality was high from the start. The operational side was not:

- long turns hit the execution budget (about five minutes in my tests) and stopped half-way,
- the same request produced duplicate PDFs,
- some turns ended in a system error.

### 4. Real engagements, checked against ground truth

With the synthetic pack passing, I pointed Debrief at completed engagements from my own portfolio (the details stay private). On the first, it found every source by itself, with the right dates and transcript segment counts, and passed 22 of 22 checks against ground truth I extracted from the transcript by hand. On a second engagement it had never seen, it picked the right company out of a group with near-identical titles, refused material from the sibling company, and said plainly that one engineer report was inaccessible instead of guessing at its contents.

It also taught me the most useful lesson of the project. One brief contained some very precise decimal metrics, and I flagged them as fabricated. Asked where they came from, the agent pointed to the automatic meeting recap, an artifact I hadn't searched. The numbers were real. The actual defect was attribution: the brief cited the transcript for figures that came from the recap. That became the rule that a recap and a transcript are separate artifacts with separate references. Verify your own accusation as rigorously as you verify the model.

### 5. Instruction bugs that look like model bugs

Most of the remaining defects traced back to my instructions, not to the model:

| Symptom | Root cause | Fix |
|---|---|---|
| Near-identical PDFs piling up | The instructions said "render the approved payload twice" (once per locale), with unique filenames and no rule against re-rendering. File hashes proved three copies were byte-identical | One filename stem per request, shared by both locales; never re-render an unchanged payload; render into a folder that holds only the two PDFs |
| A turn that never finished | An interactive shell command waited for input that was never coming | Commands must be non-interactive and self-terminating: no heredocs, REPLs, pagers or background jobs |
| "I already produced that", said to someone who couldn't see it | Clearing a Teams chat clears the client, not the server-side conversation | A behavioural reset: a different customer, "I can't see the files" or an explicit reset word starts the case over and renders again |
| Looked frozen for minutes | Long, silent turns | Exactly one short opening line, then silence until the single final message; a failed turn always ends with what completed, what failed and what is needed |
| Turns running out of budget | Tenant-wide searches even when the material was already pasted | Take the cheapest decisive path and stop searching as soon as the sources are named |

The instructions grew from roughly 17,600 to 26,700 characters, and every added rule maps to a failure I could reproduce.

### 6. Contract hours: a bridge instead of a connector

"How many hours are left?" comes up constantly, but that data lives in internal contract systems, not in Microsoft 365. A proper connector needs an OAuth custom connector and an admin-approved app registration, which is not something to finish inside a hackathon. So I built a bridge: one designated OneDrive folder with a documented CSV contract.

```text
customer, agreement, program_id, as_of_date,
contracted_hours, consumed_hours, scheduled_hours, unplanned_remaining_hours,
contract_start, contract_end, source, notes
```

The agent looks there first, takes the most recent as-of snapshot, recomputes *unplanned = contracted − consumed − scheduled* and shows the arithmetic. If the file's own remainder disagrees, it shows both numbers and asks rather than silently correcting the file. No file means "unknown", never zero.

### 7. Ten clean runs

Finally, a regression loop: delete the conversation, open a fresh one, run a scenario, check every output. Ten scenarios, ten passes, no errors and no stray files. I drove the loop with browser automation (Playwright) so that every run started from exactly the same state.

### 8. A name and an icon

"Success Program Agent" described the program, not the job, and "agent" is dead weight in a store full of agents. **Debrief** names the moment (the engagement is over, you sit down and summarise it) and it happens to contain the output: a brief.

![Three rounds of icon candidates, with the final page-counter monogram highlighted](images/icon-evolution.png)

*Three rounds of icon design. The final version turns the page into the D's negative space.*

The icon took three rounds. Round one used literal document metaphors: fine at store size, noisy at 40 pixels. Round two tried a monogram, but the page filled the letter's counter and swallowed the D. Round three made the page the D's negative space, so the letter and the document are the same shape. I picked the version without a check-mark badge, because a green tick next to an app name reads like a platform "verified" badge and I didn't want the icon to borrow trust it hadn't earned. The light version disappeared against light themes.

### 9. Publishing

Debrief is published to the Teams + Microsoft 365 channel, shared org-wide for use, and submitted to the organization's app catalog. The demo video is a slideshow of real screenshots and title cards, assembled with Pillow and ffmpeg to land at 1:52, inside the hackathon's two-minute limit.

![A request to Debrief in Microsoft 365 Copilot with a Work IQ permission prompt](images/debrief-request.png)

*Microsoft 365 Copilot asks for permission before each tool action. In Teams, each generated file needs an explicit upload approval instead.*

![Two PDF file cards, English and Turkish, sharing one filename stem](images/debrief-delivery.png)

*Delivery: two file cards, one shared filename stem, nothing else.*

## Publishing notes for other Copilot Studio builders

A few things I wish I had known up front:

- **Availability isn't discoverability.** Org-wide sharing makes the agent installable by link immediately. Appearing in store search needs an admin to approve the catalog submission in the Teams admin center, on their schedule rather than yours.
- **Rename before you submit.** The catalog submission holds the package you submitted. After a rename, resubmit, or an approved listing will carry the old name.
- **Teams caches the manifest.** The new name and icon showed up in Microsoft 365 Copilot almost immediately. Teams kept the old ones for a good while, even across an uninstall and reinstall.
- **"Remove chat history" is client-side.** The agent's server-side conversation carries on. Design for a user who can no longer see what the agent remembers.
- **Treat file cards with care.** In Teams, every generated file asks for an upload approval, and approving the same card twice uploads the file twice.
- **If Publish stays disabled, try the other portal.** Opening the agent from the regular Copilot Studio portal instead of the preview portal re-enabled publishing for me.

## Lessons

- **Put judgment in the model and rules in code.** Anything that must come out identical every time belongs in a deterministic renderer, not in a prompt.
- **Test guardrails with traps, not happy paths.** A demo made only of clean data proves nothing about what the agent will leave out.
- **Most "model bugs" were instruction bugs.** "Render twice" did exactly what it said.
- **The chat window is not the conversation.** Server-side state outlives what the user can see.
- **Verify your verification.** My fabrication accusation was wrong, and the attribution bug underneath it was real.
- **Design for the turn budget.** The cheapest decisive path beats the most thorough one.
- **The refusal is part of the product.** "Here is what I left out, and why" is the paragraph that earns trust.

## What's next

- A real contract-hours connector (an OAuth custom connector) to replace the CSV bridge
- An evaluation set in Copilot Studio, built from the synthetic regression pack
- A store listing, once the catalog submission is approved

## Repository layout

```text
.
├── README.md        this write-up
├── images/          diagrams, screenshots and page renders (all synthetic)
└── media/
    └── debrief-demo.mp4   the 1:52 demo video
```

---

*Debrief is a personal Microsoft Global Hackathon 2026 project, not an official Microsoft product or service. Every customer, person, figure and file shown here is synthetic. Opinions are my own.*
