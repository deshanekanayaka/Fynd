# The grading rule for the Retrieval set

The Retrieval set holds 40 to 60 Papers of the Seeded Topic. Every Paper carries one Relevance grade, which a person writes by hand. This file is the rule that grade follows.

Read this file before you grade, and read it again before you re-grade. A rule you keep in your head changes between the first Paper and the fortieth.

The Seeded Topic is United Kingdom household energy forecasting.

## How to grade

Read the title and the abstract. Nothing else.

Grade in the order the set file holds. That order is shuffled with a fixed seed, so it carries no rank. A list read in rank order produces agreement with the ranking, and this set exists to disagree with the ranking when the ranking is wrong.

Do not look up which query returned the Paper. The file records that for the table, not for you.

## The three grades

Grade 2 means the Paper is on the Topic. Its main subject is the Topic. A student would cite it in the Problem section of a proposal.

Grade 1 means the Paper touches the Topic. It covers one part of the Topic, or it covers the Topic in another place or another setting. It is background, and it is not the thing.

Grade 0 means the Paper is not relevant. It is about something else.

Recall counts a grade of 1 and a grade of 2 as relevant. nDCG uses all three grades, so the difference between a 1 and a 2 changes a published number.

## The worked case

A good paper on Spanish household energy forecasting is a 1 and not a 2.

The method is the Topic, and that argues for a 2. The place is not, and the place is part of the Topic. `CONTEXT.md` says a Problem is tied to a place and a group of people, so the place carries weight here.

Grade every place question the same way. A Paper about another country, another climate, or another kind of building is a 1.

## Three more cases this pool holds

A Paper about ultra-processed food is a 0. Two such Papers reached the measured pool of 2026-10-17, which is the finding this set exists to put a number on.

A Paper about United Kingdom energy that forecasts nothing, for example a survey of fuel poverty, is a 1. The place and the subject match, and the task does not.

A Paper that forecasts household electricity with no country named is a 1. An unstated place is not the Topic's place.

## What to write down

Write the grade into the `grade` field of each entry in the set file. Leave nothing at `null`.

Write the count of each grade into the measurement file when the table is published. A reader needs the denominator to read a recall number.

## The limits to state

One person grades this set, because Fynd is a solo project. There is no agreement number between two graders, and the table says so.

The set is a pool of four queries. Recall over a pool is recall inside the pool, so a relevant Paper that no query returned is invisible to every number in the table. The table says that too.
