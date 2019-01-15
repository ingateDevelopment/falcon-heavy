from __future__ import unicode_literals


def list_to_dict(l):
    """Converts list to dictionary"""
    return dict(zip(l[::2], l[1::2]))
