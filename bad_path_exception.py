class BadPathException(Exception):
    def __str__(self):
        return str(type(self))
