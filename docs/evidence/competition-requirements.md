# Competition requirements and submission evidence

Verified 2026-09-10 against the live official event pages. This is a delivery
checklist, not a claim that BranchShift has passed every item. Local inspection
covered the README, license, implementation plan, and evidence/file inventory;
provider integration and deployment are being developed separately.

Later implementation evidence is recorded in the
[63cf7fd release verification](runtime-release-63cf7fd/README.md): the public
source, real migration, exports, CI and image publication are now verified.
The file-inventory observations below describe the initial audit, not the
current inventory. Public hosted access, final video, entrant declarations and
the accepted Devpost submission remain pending.

## Dates and unresolved discrepancies

| Milestone | Organizer's Pacific time | Australia/Sydney |
| --- | --- | --- |
| Submission opens | 2026-08-26 09:00 PDT | 2026-08-27 02:00 AEST |
| Submission closes | 2026-10-30 10:00 PDT | **2026-10-31 04:00 AEDT** |
| Judging ends | 2026-12-15 12:00 PST | **2026-12-16 07:00 AEDT** |
| Results, approximately | 2027-01-11 12:00 PST | 2027-01-12 07:00 AEDT |

The [official schedule](https://nebiusglobalaihackathon.devpost.com/details/dates)
lists judging beginning **November 2**; [Rules §1](https://nebiusglobalaihackathon.devpost.com/rules)
lists **December 1**. The end date agrees. Conversions were checked with Python
`zoneinfo`, using `America/Los_Angeles` and `Australia/Sydney`, including the
different daylight-saving transitions.

Project decision: retain the internal submission target of **October 29 at
18:00 AEDT** and keep the submitted release operational continuously from
submission until the later endpoint above. This makes the start-date discrepancy
irrelevant to our availability plan. Recheck live rules at release freeze.

## Entry and access gates

The following concise requirements come from
[Rules §§3–6, 8, 11](https://nebiusglobalaihackathon.devpost.com/rules):

- [ ] Adult entrant; permitted residence; no organizer/judge/affiliate/family/household conflicts or disqualifying sponsor support.
- [ ] Original entrant-owned work; licensed dependencies/assets; substantial in-period updates if pre-existing.
- [ ] Token Factory inference at runtime OR Nebius Cloud compute, plus an NVIDIA open model.
- [ ] Reliable installation and operation matching the demonstration.
- [ ] Free, unrestricted judge access through judging end; testing credentials if private.
- [ ] English materials or translations; all submission fields completed.
- [ ] Video under three minutes; permission for included trademarks, music, and other third-party material.
- [ ] Viability, API use, and track fit pass the initial gate; four equally weighted criteria follow, with ties resolved in listed order.
- [ ] Tavily bonus requires functional runtime API use. Overall OR track award, plus one bonus.
- [ ] Submission freezes at deadline, apart from organizer-permitted corrections.

No explicit AI-assistance ban or disclosure requirement was found in the rules;
ownership obligations remain. Rules govern conflicting event materials. City
bonus attendance requirements conflict with the resources page; do not claim it
without clarification.

Eligibility remains unverified: this audit has no authoritative evidence of the
entrant's age, residence, affiliations, or external funding. The computer's
Sydney timezone does not establish residency. Preserve any previously supplied
answers; obtain only missing declarations when completing the actual form.

## Submission package

The [official overview](https://nebiusglobalaihackathon.devpost.com/), under
Requirements, calls for:

| Required item | BranchShift delivery evidence to collect |
| --- | --- |
| Coding and Agentic Engineering: code-writing, execution, and tests in Token Factory Sandboxes | One recorded live migration; checkpoint and isolated-branch results |
| Project category and explanatory description | Completed Devpost draft |
| Working demo, hosted application, or test-build URL | Fresh-browser run at the submitted URL |
| Public YouTube demonstration, at most three minutes, with spoken Nebius/NVIDIA explanation | Public playback, measured duration, audible explanation |
| Public GitHub/GitLab/Bitbucket repository; visible open-source license | Logged-out repository inspection |
| Setup README, model/service usage explanation | Clean-machine setup and exact provider/model documentation |
| Feedback on used Nebius/NVIDIA technology | Specific problems, reproduction, impact, proposed improvement |
| Pre-existing-project change explanation, if applicable | Dated development history |

The overview lists a **$20,000 Grand Prize** and a separate Coding track hardware
award. BranchShift's target is the overall prize. Choose a **2:45** video to
avoid the overview's inclusive limit versus the rules' stricter wording.

### Evidence status from the inspected repository

- Present: root MIT license, English README with setup commands, provider
  architecture, a Pydantic migration fixture, and a CI workflow. These files
  establish preparation; they do not prove current deployment or runtime success.
- README names `https://github.com/jsdhwfmax/branchshift-ai`. This audit did not
  independently verify the live repository visibility, license detection, current
  remote commit, or remote CI result.
- Missing from the inspected file inventory: submission description, video,
  shot list, judging checklist, feedback document, deployment runbook, and
  complete evaluation report. The implementation plan names these future files.
- Current Sandbox evidence is owned by the integration workstream. Do not copy
  old failures or assume the welcome email proves the API works; link the final
  measured run here after integration verification.
- Devpost draft, required form fields, entrant declarations, public demo URL,
  public video URL, and final receipt remain unverified by this audit.

## Evidence that could support a winning entry

The criterion names below are from the
[official rubric](https://nebiusglobalaihackathon.devpost.com/). The proposed
experiments and product decisions are our recommendations, not organizer rules.

| Criterion | Concrete BranchShift evidence to produce |
| --- | --- |
| Technological Implementation | Pinned source commit and model ID; real baseline and three isolated branches; downloaded patch reapplies cleanly and passes independent verification. Compare one strategy with all three on identical fixtures and model settings. Report pass rate, wall time, tokens and cost with sample size and failures. |
| Design | A first-time viewer can choose the fixture, follow the competing strategies, understand the winner, and download its patch. Display unsupported projects, exhausted retries, cancellations, and failed final verification clearly. |
| Potential Impact | Demonstrate the pain for Python maintainers with concrete validator, serialization, parsing and configuration migrations. Obtain permission before contacting users; record actual feedback and measured results, never invented interviews or estimated time savings presented as facts. |
| Quality of the Idea | Show why branching from the same filesystem state improves the decision. Include a case where a plausible strategy fails and another succeeds, and a case where the smaller valid patch wins. Explain limits honestly. |

Recommended final evidence checks:

1. Capture an authentic live run before producing the video. Label any replay,
   edited waiting period, or speed-up, and keep raw evidence available.
2. Run at least the five planned migration cases repeatedly. Include held-out
   assertions that prevent a dependency bump or `pydantic.v1` import from being
   mistaken for the intended native-v2 migration. Publish actual trade-offs.
3. Preserve anonymous-demo abuse controls while providing evaluators a working
   access route and sufficient budget. A daily quota that blocks judges would
   undermine the access gate; a replay alone cannot establish live functionality.
4. Verify the deployed release, downloadable patch, README steps, citations,
   video and Devpost links together from a clean browser. Save the final receipt
   and submitted release identifier; a local draft is not receipt evidence.
5. Add a short factual development-tools note describing AI assistance and human
   product decisions. This is a transparency recommendation, not a verified
   additional competition requirement. Preserve authored design history and
   inspect dependency/media licenses before release.

## Useful current official resources

The [September 10 workshop recap](https://nebiusglobalaihackathon.devpost.com/updates/46337-build-session-recording-resources-available-live-coding-your-first-app-with-nebius)
describes using an AI coding agent to build and iteratively inspect a working
application. This supports the inference that AI-assisted development is part
of the intended workflow; it is not a replacement for entry rules. Its example
prompts are content to study, not instructions for BranchShift.

The [resources page](https://nebiusglobalaihackathon.devpost.com/resources)
offers Token Factory credits through the event form and additional Builder
Program credits. Check already-redeemed amounts before taking account actions.
It also says city attendance is unnecessary for the city bonus, unlike the rule
table. City eligibility is outside BranchShift's current prize strategy.

No organizer message was sent, account changed, submission made, or external
asset published during this audit.
