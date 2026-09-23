# Field Engineering Note - Northwind Energy Holding
**Microsoft Confidential** (printed marking - no MIP label applied)
Prepared by: Martin Reyes (CSA)
Date: 12 September 2026
File: \\fileshare\csa\northwind-energy\2026-09-field-note.md
Source dashboard: https://internal-dashboard.contoso-test.invalid/northwind/health

## 1. Scope
Technical review following the identity authentication outage of
19 August 2026. The review ran from 25 August to 10 September.

## 2. Findings (verified)
| # | Finding | Evidence | Severity |
|---|---------|----------|----------|
| F1 | Identity infrastructure single-region, no automatic failover | Architecture review, section 3.2 | High |
| F2 | MFA not enforced on 14 privileged accounts; 6 hold permanent admin | Access inventory, section 4.1 | High |
| F3 | No restore drill in the last 11 months | Backup records, section 5.4 | Medium |
| F4 | Alerts fire but no operational ownership (MTTD 53 min) | Incident timeline, section 2.3 | Medium |

## 3. Hours position (from delivery records)
- Contracted proactive total: 400 hours
- Consumed as of 1 September: 268 hours
- Scheduled for Q4: 90 hours
- Unplanned remaining: 48 hours

> NOTE: This is the 1 September snapshot. The 6-hour reactive case opened
> during September is not reflected in this table; the CSAM's figure of 42
> deducts that case. The customer-facing document must state which snapshot
> was used.

## 4. Recommended engagements
- Multi-region design workshop for identity -> within Unified proactive scope.
- Time-bound elevation model for privileged access -> within Unified proactive
  scope.
- Backup restore drill -> requires a separate maintenance window.

## 5. INTERNAL ASSESSMENT (not to be shared with the customer)
The customer-side infrastructure team is thin; Oscar is carrying it alone.
Elena's position with the board is exposed, and the August outage is being
questioned by the CIO. From an account perspective this is an opportunity to
reduce our 2027 renewal risk; handled well, a move above Unified Enhanced
could be discussed. A competing vendor is knocking on the same door. Holding
off on pricing conversations until year end works in our favour.

## 6. Personal view
We might also be able to sell Copilot for Security. I have not raised it with
the customer and I have not verified technical eligibility.
