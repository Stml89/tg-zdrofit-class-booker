---
name: run-tests
description: Use after any changes in the code base and validating changes before release.
---

## What to do

1. Determine which tests are relevant to the change.
2. Run the required tests using `python -m unittest discover -s tests -p "test_*.py"`.
3. If the tests fail - issue(s) should be reviewed and fixed.
4. If the tests pass - changes are good.
