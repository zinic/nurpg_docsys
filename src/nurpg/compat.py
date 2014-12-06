import sys

# Compatibility work for managing user input which has changed since python
# 2.7.x to 3.x.x
user_input = input

# Compatibility for expected input functionality with 3.x.x forward
if sys.version_info[0] == 2:
    user_input = raw_input
