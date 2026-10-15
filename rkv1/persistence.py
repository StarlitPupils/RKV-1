"""Explicit per-file sync boundary; no directory/power-loss durability claim."""
import os

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
    return False  # The enclosing context closes/flushed the file as before.


def publish_directory(stage, destination):
    # Parents must be trusted; this is not a multi-writer transaction protocol.
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(destination)
    stage.rename(destination)
