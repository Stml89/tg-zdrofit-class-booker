---
name: write-tests
description: Use after completing a feature to write tests covering new functionality. Run before run-tests skill.
---

## What to do

1. Review latest feature and changes.
2. Cover new feature with tests written in python and unittest as runner.
3. Coverage should be 100%, if it is possible.
4. Branch coverage should be 100%, if it is possible.
5. Run tests using `python -m unittest discover -s tests -p "test_*.py"`.
6. If the tests fail - issue(s) should be reviewed and fixed.
7. If the tests pass - changes we are good.
