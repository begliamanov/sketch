"""The exit-code contract, the same meaning in every tool."""

OK = 0
CHECK_FAILED = 1  # a check ran and found problems
REFUSED = 2  # the tool refused: a cap was reached, or the operation is not allowed
USAGE = 3  # bad arguments or unusable input
