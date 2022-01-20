import json
import os
import sys

_dsl_schema_cache = None
_dsl_validator_cache = None

_table_admin_privs = ['SELECT', 'INSERT', 'DELETE', 'OWNERSHIP']
_table_public_privs = ['SELECT']


def dsl_json_schema():
    global _dsl_schema_cache
    if _dsl_schema_cache is not None:
        return _dsl_schema_cache

    try:
        import importlib.resources as pkg_resources
    except ImportError:
        # try 3.7 backport as a fallback
        import importlib_resources as pkg_resources

    from . import jsonschema
    with pkg_resources.open_text(jsonschema, 'dsl-schema.json') as schemafile:
        _dsl_schema_cache = json.load(schemafile)
    return _dsl_schema_cache


def dsl_json_validator():
    global _dsl_validator_cache
    if _dsl_validator_cache is not None:
        return _dsl_validator_cache
    import jsonschema
    _dsl_validator_cache = jsonschema.Draft7Validator(dsl_json_schema())
    # future work: if we ever desire to support default vales, use the following
    # to extend validation with filling in defaults from the json-schema spec
    # https://github.com/Julian/jsonschema/issues/4#issuecomment-4396738
    return _dsl_validator_cache


def dsl_to_rules(dsl: dict, validate = True) -> dict:
    """
    Transform DSL json structure to trino 'rules.json' structure

    Currently the expected format of 'dsl' parameter is only defined via the
    example dsl files in the examples directory, for example here:
    https://github.com/os-climate/osc-trino-acl-dsl/blob/main/examples/dsl-example-1.json

    This function returns a 'dict' structure that can be written using 'json.dump' to produce
    a 'rules.json' file ingestable by trino.
    """
    if validate:
        # validate the dsl json structure against the DSL json-schema
        dsl_json_validator().validate(dsl)

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
    for spec in dsl['tables']:
        public = spec['public']
        # table admin group rules go first to override others
        table_rules.append({
            "group": "|".join(spec['admin_groups']),
            "catalog": spec['catalog'],
            "schema": spec['schema'],
            "table": spec['table'],
            "privileges": _table_admin_privs
            })
        # detect row-level access if it was configured
        rafilter = None
        if "row_acl" in spec:
            rowspec = spec['row_acl']
            rstype = rowspec['type']
            if rstype == "filter":
                rafilter = rowspec['filter']
            else:
                raise ValueError(f"unrecognized row_acl type {rstype}")
        # construct column access rules if any are configured
        hcols = []
        if "column_acl" in spec:
            for hspec in spec['column_acl']:
                hcols.extend(hspec['hide_columns'])
                if "groups" in hspec:
                    rule = {
                        "group": "|".join(hspec['groups']),
                        "catalog": spec['catalog'],
                        "schema": spec['schema'],
                        "table": spec['table'],
                        "privileges": _table_public_privs
                    }
                    if rafilter: rule["filter"] = rafilter
                    if len(hcols) > 0:
                        rule["columns"] = [{"name": col, "allow": False} for col in hcols]
                    table_rules.append(rule)
        # table default policy goes last
        rule = {
            "catalog": spec['catalog'],
            "schema": spec['schema'],
            "table": spec['table'],
            "privileges": _table_public_privs if spec['public'] else []
        }
        if rafilter and public: rule["filter"] = rafilter
        if (len(hcols) > 0) and public:
            rule["columns"] = [{"name": col, "allow": False} for col in hcols]
        table_rules.append(rule)

    # next are schema rules
    for spec in dsl['schemas']:
        # configure group(s) with ownership of this schema
        schema_rules.append({
            "group": "|".join(spec['admin_groups']),
            "catalog": spec['catalog'],
            "schema": spec['schema'],
            "owner": True
            })
        # schema rules for tables section are lower priority than table-specific above
        table_rules.append({
            # ensure that schema admins also have full table-level privs inside their schema
            "group": "|".join(spec['admin_groups']),
            "catalog": spec['catalog'],
            "schema": spec['schema'],
            "privileges": _table_admin_privs
            })
        table_rules.append({
            # set the default public privs inside this schema
            "catalog": spec['catalog'],
            "schema": spec['schema'],
            "privileges": _table_public_privs if spec['public_tables'] else []
            })

    # next are catalog rules
    for spec in dsl['catalogs']:
        # configure group(s) with read+write access to this catalog
        catalog_rules.append({
            "group": "|".join(spec['admin_groups']),
            "catalog": spec['catalog'],
            "allow": "all"
            })
        # catalog rules for tables section are lower priority than schema rules above
        table_rules.append({
            "catalog": spec['catalog'],
            "privileges": _table_public_privs if spec['public_tables'] else []
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

    rules = dsl_to_rules(dsl, validate = True)

    with sys.stdout as rules_file:
        json.dump(rules, rules_file, indent=4)
        rules_file.write('\n')

if __name__ == "__main__":
        main()
