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
    for catspec in dsl['catalogs']:
        catalog_rules.append({
            "group": "|".join(catspec['allow_groups']),
            "catalog": catspec['catalog'],
            "allow": "all"
            })
        # catalog rules for tables section are lower priority than schema rules above
        table_rules.append({
            "catalog": catspec['catalog'],
            "privileges": _table_public_privs if catspec['public_tables'] else []
            })

    # global default rules go last
    table_rules.append({
        # default table privs can be 'read-only' (i.e. select) or 'no privileges'
        "privileges": _table_public_privs if dsl['public_tables'] else []
        })
    schema_rules.append({
        # defaulting all schemas to owner is not safe
        # schemas should be assigned ownership on an explicit basis
        "owner": False
        })
    catalog_rules.append({
        # allows basic 'show schemas' and 'show tables' operations for everyone
        "allow": "read-only" 
        })

    # assemble the final json structure and return it
    rules = {
        "catalogs": catalog_rules,
        "schemas": schema_rules,
        "tables": table_rules
    }
    return rules

def main():
    dsl_json_fname = sys.argv[1]

    with open(dsl_json_fname, 'r') as dsl_file:
        # future work: support both json and yaml, probably use pyyaml lib
        dsl = json.load(dsl_file)

    # future work: add a json-schema spec for validation, and use the following
    # to extend validation with filling in defaults from the json-schema spec
    # https://github.com/Julian/jsonschema/issues/4#issuecomment-4396738

    rules = dsl_to_rules(dsl)

    with sys.stdout as rules_file:
        json.dump(rules, rules_file, indent=4)
        rules_file.write('\n')

if __name__ == "__main__":
        main()
