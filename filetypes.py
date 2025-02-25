import util

kPictureExts = [ \
    "bmp", \
    "gif", \
    "jpeg", \
    "jpg", \
    "nef", \
    "png", \
    "psd", \
    "svg", \
    "tga", \
    "tif", \
    "tiff" \
    ]

kMovieExts = [ \
    "3gp", \
    "avi", \
    "mov", \
    "mp4", \
    "mpeg", \
    "mpg", \
    "wmv" \
    ]

def is_picture( ext ):
    return ext in kPictureExts

def is_movie( ext ):
    return ext in kMovieExts


