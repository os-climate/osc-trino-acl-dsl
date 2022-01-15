import json
import os
import sys

_table_admin_privs = ['SELECT', 'INSERT', 'DELETE', 'OWNERSHIP']
_table_public_privs = ['SELECT']

def dsl_to_rules(dsl: dict) -> dict:
    """Transform DSL json structure to trino "rules.json" structure"""
    catalog_rules = []
    schema_rules = []
    table_rules = []

    # rules configuring admin acl go first to ensure they override anything else
    catalog_rules.append({
        "group": "|".join(dsl['admin_groups']),
        "allow": "all"
        })
    schema_rules.append({
        "group": "|".join(dsl['admin_groups']),
        "owner": True
        })
    table_rules.append({
        "group": "|".join(dsl['admin_groups']),
        "privileges": _table_admin_privs
        })

    # table rules go here

    # next are schema rules

    # next are catalog rules

    # global default rules go last
    catalog_rules.append({
        "allow": "all" if dsl['public_catalogs'] else "none"
        })
    schema_rules.append({
        "owner": True if dsl['public_schemas'] else False
        })
    table_rules.append({
        "privileges": _table_public_privs if dsl['public_tables'] else []
        })

    rules = {
        "catalogs": catalog_rules,
        "schemas": schema_rules,
        "tables": table_rules
    }
    return rules

def main():
    dsl_json_fname = sys.argv[1]
    rules_json_fname = sys.argv[2]

    with open(dsl_json_fname, 'r') as dsl_file:
        # future work: support both json and yaml, probably use pyyaml lib
        dsl = json.load(dsl_file)

    # future work: add a json-schema spec for validation, and use the following
    # to extend validation with filling in defaults from the json-schema spec
    # https://github.com/Julian/jsonschema/issues/4#issuecomment-4396738

    rules = dsl_to_rules(dsl)

    with open(rules_json_fname, 'w') as rules_file:
        json.dump(rules, rules_file, indent=4)
        rules_file.write('\n')

if __name__ == "__main__":
        main()
