"""Select a decoder only inside isolated benchmark workers."""


def select_csv_decoder(variant="current"):
    from .. import core
    if variant == "current":
        from ..transforms import csv_columns_decode
    elif variant == "v0.3.0":
        from .csv_v0_3 import csv_columns_decode
    else:
        raise ValueError("Unknown experimental CSV decoder")
    core.csv_columns_decode = csv_columns_decode
