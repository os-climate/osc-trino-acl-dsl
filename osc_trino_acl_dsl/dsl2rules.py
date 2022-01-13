import json
import os
import sys

def dsl_to_rules(dsl: dict) -> dict:
    """Transform DSL json structure to trino "rules.json" structure"""
    catalog_rules = []
    schema_rules = []
    table_rules = []
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
        dsl = json.load(dsl_file)

    rules = dsl_to_rules(dsl)

    with open(rules_json_fname, 'w') as rules_file:
        json.dump(rules, rules_file, indent=4)
        rules_file.write('\n')

if __name__ == "__main__":
    main()
