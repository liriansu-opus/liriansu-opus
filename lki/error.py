class LKIError(Exception):
    """ Something's happening, but don't panic """

    def __init__(self, message=None):
        super(LKIError, self).__init__(message or self.__doc__.strip())

    @classmethod
    def check(cls, condition, message=None):
        if condition:
            raise cls(message)


class LinkError(LKIError):
    pass
