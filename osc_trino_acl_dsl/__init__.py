"""
osc-trino-acl-dsl

A DSL for generating rules.json files for Trino
"""

# defines the release version for this python package
__version__ = "0.2.4"

from .dsl2rules import *

__all__ = [
    "dsl_to_rules",
    "dsl_json_schema",
    "dsl_json_validator",
]

