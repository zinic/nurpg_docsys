class ErrorMessage(Exception):

    def __init__(self, msg=None):
        self.msg = msg


# Return values

OKAY = 0
GENERAL_FAILURE = 1
BAD_DOCUMENT = 2
CONFIGURATION_ERROR = 10
NODE_NOT_FOUND = 100
