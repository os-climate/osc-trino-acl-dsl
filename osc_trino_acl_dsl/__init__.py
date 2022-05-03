"""
osc-trino-acl-dsl

A DSL for generating rules.json files for Trino
"""

from .dsl2rules import dsl_json_schema, dsl_json_validator, dsl_to_rules

__all__ = [
    "dsl_to_rules",
    "dsl_json_schema",
    "dsl_json_validator",
]
