import os

def px( path ):
    if "/" in path and "/" != os.path.sep:
        return path.replace("/", os.path.sep)
    else:
        return path

