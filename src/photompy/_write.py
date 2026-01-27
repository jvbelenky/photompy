"""
Internal write helpers.

This module contains helper functions for writing IES files.
These are internal implementation details, not part of the public API.
"""


def process_row(row, sigfigs=2):
    """Format a row of numbers for IES file output with line wrapping."""
    total = 0
    newstring = ""
    for i, number in enumerate(row):
        if total > 76:
            newstring += "\n"
            total = 0
        numberstring = str(round(number, sigfigs))
        newstring += numberstring
        total += len(numberstring)
        if i != len(row) - 1:
            # don't add extra characters if it's the end of the file
            if total > 76:
                newstring += "\n"
                total = 0
            newstring += " "
            total += 1
    if newstring[-4:] != "\n":
        newstring += "\n"
    return newstring
