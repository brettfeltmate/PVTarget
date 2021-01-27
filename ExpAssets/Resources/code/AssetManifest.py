# this is an incredibly unnecessary class written because Jon is obsessed with encapsulation and prefers dot notation
try:
	from collections.abc import MutableMapping
except ImportError:
	from collections import MutableMapping


class DotDict(MutableMapping):
	__getattr__ = dict.__getitem__
	__setattr__ = dict.__setitem__
	__delattr__ = dict.__delitem__
