"""Nothing here generates a bundled dataset any more.

All three -- titanic, tips and diamonds -- used to be simulated from
distributions chosen to give them the right shape, then written to files whose
names promise the well-known originals. The numbers did not match: the Titanic
showed 438 survivors against the true 342, tips a mean of 3.98 against 3.00,
diamonds a mean price of 2361.73 against 3932.80. Nothing said so anywhere, so
a student who looked one up, or brought their own copy, got a different answer
with no explanation.

The real data ships in the package now, with provenance in each dataset's
SOURCE.md. This module stays because CI and the install docs call it, and
because an empty run is better than a missing command -- but it must never
regenerate those three files again.

Run: python -m pyanalytica.datasets.generate
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

_DIR = Path(__file__).parent
_RNG = np.random.default_rng(42)


# generate_titanic() was removed in 0.9.0.
#
# It built a simulated passenger list from distributions chosen to resemble the
# real one, and wrote it to titanic.csv. The result had 438 survivors against
# the true 342, and nothing told the student it was not the Titanic. The real
# passenger list ships in the package instead; see datasets/titanic/SOURCE.md.
#
# Nothing regenerates that file now. Leaving a generator here would put the
# simulated data back on the next CI run, which regenerates the datasets before
# every test.


def main():
    print("Generating PyAnalytica bundled datasets...")
    print("Done!")


if __name__ == "__main__":
    main()
