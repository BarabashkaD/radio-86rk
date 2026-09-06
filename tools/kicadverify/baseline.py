"""Baseline capture and metadata. Task 8 fills this in."""
import json
import os


def read_meta(baseline_dir):
    """The captured baseline's metadata, or None if there is no baseline."""
    path = os.path.join(baseline_dir, "meta.json")
    if not os.path.exists(path):
        return None
    with open(path) as handle:
        return json.load(handle)
