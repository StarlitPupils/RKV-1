"""Explicit per-file sync boundary; no directory/power-loss durability claim."""
import os
import time

POLICIES = ("files", "close")


def validate_policy(policy):
    if not isinstance(policy, str) or policy not in POLICIES:
        raise ValueError("Invalid restore sync policy")


def finish_file(stream, policy):
    """Called only after the complete original file hash has been verified."""
    validate_policy(policy)
    if policy == "files":
        stream.flush()
        os.fsync(stream.fileno())
        return True
    return False  # The enclosing context closes and flushes the file as before.


def _transient_windows_rename(error):
    return os.name == "nt" and getattr(error,"winerror",None) in (5,32,33)


def publish_directory(stage, destination):
    # Parents must be trusted; this is not a multi-writer transaction protocol.
    delays=(.01,.05,.1)
    for attempt in range(4):
        if destination.exists() or destination.is_symlink():
            raise FileExistsError(destination)
        try:
            stage.rename(destination)
            return attempt+1
        except OSError as error:
            if attempt==3 or not _transient_windows_rename(error):
                raise
            time.sleep(delays[attempt])
