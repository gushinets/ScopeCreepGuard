import copy
import json
from pathlib import Path


def editor(**changes):
    raw = json.loads(
        (Path(__file__).parents[2] / "contracts/compatibility/any-640/drafts.json").read_text(
            encoding="utf-8"
        )
    )["base"]["document"]["changeOrder"]
    return {**copy.deepcopy(raw), **changes}
