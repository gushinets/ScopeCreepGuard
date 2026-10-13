"""LLM integrations use the pinned local capability map, never fetch prices at import."""

import os

os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"
