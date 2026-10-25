"""Lossless evidence storage; semantic representations never replace source bytes."""

from .core import Archive, assert_tree_equal, pack, unpack, verify

__version__ = "0.29.0"
__all__ = ["Archive", "assert_tree_equal", "pack", "unpack", "verify"]
