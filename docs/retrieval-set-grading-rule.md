# The grading rule for the Retrieval set

The Retrieval set holds 60 Papers of the Seeded Topic. Every Paper carries one Relevance grade, which a person writes by hand. This file is the rule that grade follows.

Read this file before you grade, and read it again before you re-grade. A rule you keep in your head changes between the first Paper and the sixtieth.

The Seeded Topic is United Kingdom household energy forecasting.

## The one thing this rule is about

Grade the subject, which is household energy forecasting. Ignore the country.

A Paper's country does not decide its worth to a student. `CONTEXT.md` gives the place to a Statistic, which is a published figure from an official body that shows the Problem is real in one place, for example an Office for National Statistics release. `PRD.md` then makes stage 3 demand at least one Claim from a Statistic or a Product, so the place is proven there.

A Paper carries the Existing approach and the Technical core instead. Neither one has a place, and neither one has a date limit, which is why the Evidence window does not apply to them. A Korean paper on household load forecasting is first class evidence for both.

So a rule that marked a Spanish paper down would teach the ranking to prefer a paper that merely mentions the United Kingdom over a paper that holds the method a student needs. The measured pool already holds two of those, which are a policy model of the United Kingdom and a comparison of artificial intelligence governance.

## How to grade

Read the title and the abstract. Nothing else.

Grade in the order the command shows them. That order is shuffled with a fixed seed, so it carries no rank. A list read in rank order produces agreement with the ranking, and this set exists to disagree with the ranking when the ranking is wrong.

Do not look up which query returned the Paper. The file records that for the table, not for you.

## The three grades

Grade 2 means the Paper is on the subject. It forecasts or predicts household or residential energy, electricity, gas or heat. The country does not matter, and neither does the method.

Grade 1 means the Paper covers part of the subject. It forecasts energy that is not household energy, for example a national grid or a wind farm. Or it studies household energy and forecasts nothing, for example a survey of fuel poverty. Or it names no energy at all and gives a method a household forecaster would use.

Grade 0 means the Paper is not relevant. It is about another subject.

Recall counts a grade of 1 and a grade of 2 as relevant. nDCG uses all three grades, so the difference between a 1 and a 2 changes a published number.

## The worked cases

A good paper on Spanish household energy forecasting is a 2. The subject is the subject, and the country belongs to a Statistic and not to a Paper.

A paper that forecasts household electricity with no country named is a 2, for the same reason.

A paper about ultra-processed food is a 0. Two such Papers reached the measured pool of 2026-10-17, which is the finding this set exists to put a number on.

`Energy and Climate Policy in a DSGE Model of the United Kingdom` is a 1. It names the country and it is not a household forecast, so the country alone earns nothing.

`Load Forecasting Models in Smart Grid Using Smart Meter Information: A Review` is a 2. A review of the exact subject is still the subject.

A paper that forecasts the load of a national grid is a 1. The subject is energy forecasting and the unit is not a household.

## What to write down

The command writes the grade into the `grade` field of each entry. Leave nothing at `null`.

Write the count of each grade into the measurement file when the table is published. A reader needs the denominator to read a recall number.

## The limits to state

One person grades this set, because Fynd is a solo project. There is no agreement number between two graders, and the table says so.

The set is a pool of four queries. Recall over a pool is recall inside the pool, so a relevant Paper that no query returned is invisible to every number in the table. The table says that too.

The grade ignores the country, so no number in the table says anything about whether Fynd finds United Kingdom evidence. Three of the four queries name the country and one does not, so the per query rows are the only place that question shows at all.
