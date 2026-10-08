# Fynd

Fynd helps a final year project student start from a real problem with evidence behind it, instead of from an app idea. It narrows a domain to a topic, gathers evidence, shows what already exists, and drafts a proposal the student takes to a supervisor.

The student is a bachelor's student. The project they must deliver is a full stack application with background research, requirements, a database design, and an API design. Fynd therefore proposes software a student can build in one academic year, not a research contribution.

## Language

**Project**:
One student's pass through Fynd, from topic to proposal. Reachable by a secret link, with no login.
_Avoid_: session, workspace, report

**Stage**:
One of the seven numbered steps of a Project, from Domain to export. Every Stage is saved and resumable.
_Avoid_: step, phase, screen, page

**Stage state**:
What one Stage saved. It holds enough to resume the Project without running the Stage again.
_Avoid_: progress, checkpoint, snapshot, session data

**Pick**:
The one item a student chooses from what a Stage offered, kept with the Stage it answers.
_Avoid_: choice, selection, option, answer

**Re-roll**:
A student's request for a new set of items from a Stage, instead of choosing one of the items it offered. Stage 2 and stage 3 allow one each.
_Avoid_: retry, refresh, regenerate, shuffle

**Domain**:
A broad field the student picks first, for example Technology, Healthcare, or Energy.
_Avoid_: industry, area

**Topic**:
The narrow area a Project works inside, for example household energy forecasting. A Domain holds many Topics.
_Avoid_: subfield, niche, keyword

**Seeded Topic**:
The one Topic fixed in the repository. The labelled set and the regression tests run against it.
_Avoid_: test topic, default topic, example

**Problem**:
The real situation the student's software will address, stated in plain words and tied to a place and a group of people. A Problem can already have solutions.
_Avoid_: pain point, use case, research question

**Candidate Problem**:
One of the 3 Problems Fynd drafts at stage 3, each with 2 Claims. The student picks one.
_Avoid_: problem candidate, option, suggestion

**Source**:
Anything Fynd cites. A Source is a Paper, a Statistic, or a Product.
_Avoid_: reference, link, document, result

**Paper**:
One published academic work, with its identifiers, title, abstract, and a link to an open copy if one exists.
_Avoid_: article, publication, study

**Open copy**:
The free file of a Paper, held in a repository. Fynd fetches an Open copy and never fetches a publisher page.
_Avoid_: open access PDF, free version, preprint

**Source text**:
The one exact string that extraction produced for a Source. A Claim points into it with two character offsets, and the text that passes the quality checks is usable text.
_Avoid_: content, body, raw text, full text

**Statistic**:
A published figure or rule from an official body that shows the Problem is real, for example an Office for National Statistics release.
_Avoid_: data point, evidence, fact

**Product**:
An existing commercial tool that already addresses the Problem. A Product is evidence of demand, not a reason to stop.
_Avoid_: competitor, app, tool, solution

**Existing approach**:
One way the Problem is addressed today, drawn from a Paper or a Product, with what it does and where it falls short.
_Avoid_: prior art, related work, competitor analysis

**Claim**:
One sentence from one Source, kept with its citation. A Claim either shows the Problem is real or states a shortcoming of an Existing approach.
_Avoid_: limitation, finding, insight, quote

**Evidence window**:
The 5 year age limit on a Source whose Claim proves a Problem is real. An Existing approach and a Technical core carry no limit.
_Avoid_: recency filter, date cutoff, freshness

**Gap**:
The shortcoming that several Existing approaches share, supported by Claims from independent Sources. The Gap is what a Proposal aims at.
_Avoid_: opportunity, niche, white space

**Proposal**:
A full stack software idea that answers a Gap. It names a Technical core, a Point of difference, and an evaluation plan with a baseline.
_Avoid_: idea, solution, pitch, recommendation

**Technical core**:
The one part of a Proposal that is harder than reading and writing database rows, for example a forecasting model or a recommender. Every Proposal must name one, and must cite the Source it comes from.
_Avoid_: novelty, algorithm, secret sauce, ML bit

**Point of difference**:
The one sentence that says how a Proposal differs from the Existing approaches it cites.
_Avoid_: novelty, contribution, USP

**Shortlist**:
The set of Sources the student keeps as relevant. Only shortlisted Sources get a deep read.
_Avoid_: screening, triage, selection, filter

**Invite**:
A signed code in a link that lets one visitor create Projects. Fynd has no accounts and no passwords.
_Avoid_: token, licence, access key
