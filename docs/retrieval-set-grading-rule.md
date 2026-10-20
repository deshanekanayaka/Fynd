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

The command shows both. It reads the abstract from the disk cache of the search that found the Paper, and it writes the abstract nowhere, because [ADR 0011](./adr/0011-the-public-repository-holds-the-text-and-not-the-files.md) keeps an abstract out of this public repository.

8 of the 60 Papers have no abstract anywhere in the cache, because Semantic Scholar holds none for them. The command says so and you grade the title alone. The table states that as a limit.

The results and the conclusion of a Paper would be better evidence than the abstract, and they are out of reach. The measured runs say 5 of 20 Papers reach a full text Fynd can read, so a rule that asked for the conclusion would be ungradeable for most of the set.

Grade in the order the command shows them. That order is shuffled with a fixed seed, so it carries no rank. A list read in rank order produces agreement with the ranking, and this set exists to disagree with the ranking when the ranking is wrong.

Do not look up which query returned the Paper. The file records that for the table, not for you.

## The two questions

Every grade comes from these two questions, in this order. The abstract almost always answers both, and the dataset sentence answers the first one more reliably than the title does.

**Question 1. Whose energy is it?**

It is household energy when the abstract says household, home, dwelling, residential, domestic, consumer, appliance, behind-the-meter, or a smart meter at a customer's property. An abstract that says it used half-hourly readings from 5,000 households has answered yes, whatever the title said.

It is not household energy when the unit is a feeder, a substation, a city, a region, a country, a national grid, a power plant, or a commercial building.

**Question 2. Does it predict a future value?**

It predicts when the abstract says forecast, forecasting, predict, prediction, or the estimation of a future demand.

It does not predict when the abstract only describes, measures, surveys, assesses, reviews, compares, or explains something that already happened. A review of forecasting methods is the exception, and it counts as predicting, because it is about the task.

**Then the grade follows. Question 1 is the gate, and question 2 is the grade.**

The unit is not a household, so the grade is 0. Whatever it forecasts, and however good it is.

The unit is a household and it predicts, so the grade is 2.

The unit is a household and it does not predict, so the grade is 1.

Nothing else earns a 1. A national forecast, a city forecast, a grid forecast and a solar plant forecast are all 0, because they fail the gate. This is stricter than it feels, and the reason is the measurement. A pool where 51 of 60 Papers count as relevant leaves recall at 20 unable to tell a good ranking from a random one.

## What to ignore

Ignore the country. Ignore the method, so a transformer, a random forest and a plain regression are all equal here. Ignore the journal, the year and the length. None of them changes what the Paper is about.

## The three grades

Grade 2 means household energy, forecast. The Paper predicts household or residential energy, electricity, gas or heat. The country does not matter, and neither does the method, and neither does the angle the Paper takes on the problem. A privacy study of household forecasting is still a 2, and so is an explainability study of it.

Grade 1 means household energy, not forecast. The Paper studies household energy and predicts nothing, for example a survey of fuel poverty, an intervention study, or a dataset paper.

Grade 0 means the unit is not a household. A national or city electricity forecast is a 0. A grid, substation or feeder forecast is a 0. A power plant or solar generation forecast is a 0. A paper about another subject entirely is a 0.

Recall counts a grade of 1 and a grade of 2 as relevant. nDCG uses all three grades, so the difference between a 1 and a 2 changes a published number.

## The one case that still needs judgement

A smart meter sits at a customer's property, so a Paper that forecasts from smart meter readings usually passes the gate and is a 2.

It is a 0 when the Paper aggregates those readings away before forecasting. `Artificial Neural Network Based Short-Term Load Forecasting of Nuwakot Distribution Center Using Smart Meter AMI Data` says it forecasts "on the aggregate level for a distribution network", so the unit is the network and not the household. `Load Forecasting Models in Smart Grid Using Smart Meter Information: A Review` is about smart grid operation, so it is a 0 for the same reason.

Read the abstract for the unit the forecast is made at, not for the unit the data came from.

## The worked cases

A good paper on Spanish household energy forecasting is a 2. The country belongs to a Statistic and not to a Paper.

A paper that forecasts household electricity with no country named is a 2, for the same reason.

A paper about ultra-processed food is a 0. Two such Papers reached the measured pool of 2026-10-17, which is the finding this set exists to put a number on.

`Energy and Climate Policy in a DSGE Model of the United Kingdom` is a 1. Households consume the energy it models, and it simulates a policy instead of predicting demand.

`Predicting Electricity Consumption in the Kingdom of Saudi Arabia` is a 0. It forecasts well and the unit is a country.

`High-resolution smart meter load dataset collected from multiple cities in Morocco` is a 1. The readings are residential and the paper publishes data instead of a forecast.

## What to write down

The command writes the grade into the `grade` field of each entry. Leave nothing at `null`.

Write the count of each grade into the measurement file when the table is published. A reader needs the denominator to read a recall number.

## The limits to state

One person grades this set, because Fynd is a solo project. There is no agreement number between two graders, and the table says so.

The set is a pool of four queries. Recall over a pool is recall inside the pool, so a relevant Paper that no query returned is invisible to every number in the table. The table says that too.

The grade ignores the country, so no number in the table says anything about whether Fynd finds United Kingdom evidence. Three of the four queries name the country and one does not, so the per query rows are the only place that question shows at all.
