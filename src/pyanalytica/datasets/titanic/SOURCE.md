# titanic.csv

The passenger list from the RMS Titanic, as distributed in the well-known
891-row training split: `PassengerId`, `Survived`, `Pclass`, `Name`, `Sex`,
`Age`, `SibSp`, `Parch`, `Ticket`, `Fare`, `Cabin`, `Embarked`.

**This is the real data.** It agrees with the published figures a student will
find if they look the story up:

| | |
|---|---|
| Passengers | 891 |
| Survived | 342 (38.4%) |
| Male / female | 577 / 314 |
| Missing `Age` | 177 |
| Missing `Embarked` | 2 |

Until 0.9.0 this file held a *simulated* dataset generated from distributions
chosen to resemble the real one. It had 438 survivors -- a 49.2% survival rate
against the true 38.4% -- and nothing anywhere said it was synthetic. A student
who knew the story, looked it up, or brought in their own copy got a different
answer with no explanation, and any coursework quoting a published figure could
not be reconciled. See `docs/DATASETS.md`.

The missing values are part of the record and are left in: 177 passengers have
no recorded age, which is the fact that makes this a good teaching set.
