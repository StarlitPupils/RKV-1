"""Instance-local CAS implementation selection for controlled experiments."""
from .store import Store


def store_class(settings):
    implementation = settings.get("store_implementation", "current")
    if implementation == "v0.8":
        from .store_v0_8 import Store as FrozenStore
        return FrozenStore, {}
    if implementation == "current":
        return Store, {"io_backend": settings.get("io_backend", "reference"),
                       "publisher": settings.get("publisher", "link")}
    raise ValueError("Unknown CAS implementation")


def open_store(root, settings):
    cls, options = store_class(settings)
    return cls(root, **options)


def create_store(root, settings):
    cls, options = store_class(settings)
    return cls.create(root, compression=settings["compression"], chunker=settings["chunker"],
                      chunk_size=settings["chunk_size"], **options)
