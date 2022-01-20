"""
osc-trino-acl-dsl

A DSL for generating rules.json files for Trino
"""

# defines the release version for this python package
__version__ = "0.1.0"

from .dsl2rules import *

__all__ = [
    "dsl_to_rules",
    "dsl_json_schema",
]

