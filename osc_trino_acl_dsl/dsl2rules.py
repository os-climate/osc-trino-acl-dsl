import json
import sys

# from pyyaml package
import yaml

_dsl_schema_cache = None
_dsl_validator_cache = None

_table_admin_privs = ["SELECT", "INSERT", "DELETE", "OWNERSHIP"]
_table_public_privs = ["SELECT"]


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

    with pkg_resources.open_text(jsonschema, "dsl-schema.json") as schemafile:
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


def _acl_groups(jobj: dict, k="admin") -> list:
    return [e["group"] for e in jobj[k] if ("group" in e)]


def _acl_users(jobj: dict, k="admin") -> list:
    return [e["user"] for e in jobj[k] if ("user" in e)]


# python is so dumb
def _union(d1: dict, d2: dict) -> dict:
    """equivalent to (d1 | d2) in py >= 3.9"""
    u = d1.copy()
    u.update(d2)
    return u


# so dumb
def _concat(l1: list, l2: list) -> list:
    c = l1.copy()
    c.extend(l2)
    return c


def dsl_to_rules(dsl: dict, validate=True) -> dict:  # noqa: C901
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

    # mypy type checking may prefer these be typed but needs py3.9 to
    # support clean list[dict] type annotation
    catalog_rules = []
    schema_rules = []
    table_rules = []

    # rules configuring admin acl go first to ensure they override anything else
    ugs = _acl_groups(dsl)
    if len(ugs) > 0:
        # if any group entries were present, insert corresponding admin rules
        catalog_rules.append({"group": "|".join(ugs), "allow": "all"})
        schema_rules.append({"group": "|".join(ugs), "owner": True})
        table_rules.append({"group": "|".join(ugs), "privileges": _table_admin_privs})
    ugs = _acl_users(dsl)
    if len(ugs) > 0:
        # if any user entries were present, insert corresponding admin rules
        catalog_rules.append({"user": "|".join(ugs), "allow": "all"})
        schema_rules.append({"user": "|".join(ugs), "owner": True})
        table_rules.append({"user": "|".join(ugs), "privileges": _table_admin_privs})

    # any schema or table admins require "allow":"all" on the associated catalog
    # so it is most effective to just accumulate these and add corresponding rules
    # in the catalog section
    # https://trino.io/docs/current/security/file-system-access-control.html#catalog-schema-and-table-access
    # note there is not a similar issue for table -> schema ownerships
    uallow: dict = {}

    # the semantic definition for schema admin is that it includes
    # admin over any table in that schema, so these rules need to appear before other table
    # related rules
    for spec in dsl["schemas"]:
        cst = {"catalog": spec["catalog"], "schema": spec["schema"]}
        # configure group(s) with ownership of this schema
        ugs = _acl_groups(spec)
        if len(ugs) > 0:
            schema_rules.append(_union(cst, {"group": "|".join(ugs), "owner": True}))
            # ensure that schema admins also have full table-level privs inside their schema
            table_rules.append(_union(cst, {"group": "|".join(ugs), "privileges": _table_admin_privs}))
        # add corresponding rules for any user patterns
        ugs = _acl_users(spec)
        if len(ugs) > 0:
            schema_rules.append(_union(cst, {"user": "|".join(ugs), "owner": True}))
            table_rules.append(_union(cst, {"user": "|".join(ugs), "privileges": _table_admin_privs}))
        uallow[spec["catalog"]] = _concat(uallow.get(spec["catalog"], []), spec["admin"])

    # table rules go here
    for spec in dsl["tables"]:
        cst = {"catalog": spec["catalog"], "schema": spec["schema"], "table": spec["table"]}
        # "admin" is optional for any individual table because schema admins
        # are also table admins for any table in the schema
        if "admin" in spec:
            # table admin group rules go first to override others
            rule = _union(cst, {"privileges": _table_admin_privs})
            ugs = _acl_groups(spec)
            if len(ugs) > 0:
                table_rules.append(_union({"group": "|".join(ugs)}, rule))
            ugs = _acl_users(spec)
            if len(ugs) > 0:
                table_rules.append(_union({"user": "|".join(ugs)}, rule))
            uallow[spec["catalog"]] = _concat(uallow.get(spec["catalog"], []), spec["admin"])
        # construct acl rules if any are configured
        uhide = set()
        ufilter = set()
        if "acl" in spec:
            for acl in spec["acl"]:
                rule = _union(cst, {"privileges": _table_public_privs})
                if "hide" in acl:
                    uhide.update(set(acl["hide"]))
                    rule.update({"columns": [{"name": col, "allow": False} for col in acl["hide"]]})
                if "filter" in acl:
                    ufilter.update(set(acl["filter"]))
                    rule.update({"filter": " and ".join([f"({f})" for f in acl["filter"]])})
                ugs = _acl_groups(acl, k="id")
                if len(ugs) > 0:
                    table_rules.append(_union({"group": "|".join(ugs)}, rule))
                ugs = _acl_users(acl, k="id")
                if len(ugs) > 0:
                    table_rules.append(_union({"user": "|".join(ugs)}, rule))
        # table default policy goes last
        # spec['public'] can be either boolean or an object, and it
        # registers as True if it is an object or boolean value True
        public = spec["public"]
        pub = ((type(public) == bool) and public) or (type(public) == dict)
        rule = _union(cst, {"privileges": (_table_public_privs if pub else [])})
        if type(public) == dict:
            # if 'public' was specified as an object with settings, then
            # include these in the union of all hidden columns and filters
            if "hide" in public:
                uhide.update(set(public["hide"]))
            if "filter" in public:
                ufilter.update(set(public["filter"]))
        if pub:
            # if table is set to general public access, then include
            # all hidden columns and row filters in the acl list, so that
            # public cannot see anything hidden by any other row/col ACL rule
            if len(uhide) > 0:
                rule.update({"columns": [{"name": col, "allow": False} for col in sorted(list(uhide))]})
            if len(ufilter) > 0:
                rule.update({"filter": " and ".join([f"({f})" for f in sorted(list(ufilter))])})
        table_rules.append(rule)

    # default schema rules for tables are lower priority than specific table rules
    for spec in dsl["schemas"]:
        cst = {"catalog": spec["catalog"], "schema": spec["schema"]}
        # set the default public privs inside this schema
        table_rules.append(_union(cst, {"privileges": _table_public_privs if spec["public"] else []}))

    # next are catalog rules
    for spec in dsl["catalogs"]:
        rule = {"catalog": spec["catalog"], "allow": "all"}
        # configure group(s) with read+write access to this catalog
        # I have concerns about how using "|" style regex is going to scale if number
        # of schemas and tables grows large, so I am going to encode these as individual rules
        ugs = list(set([e["group"] for e in uallow.get(spec["catalog"], []) if "group" in e]))
        for ug in ugs:
            catalog_rules.append(_union({"group": ug}, rule))
        ugs = list(set([e["user"] for e in uallow.get(spec["catalog"], []) if "user" in e]))
        for ug in ugs:
            catalog_rules.append(_union({"user": ug}, rule))

        # catalog rules for tables section are lower priority than schema rules above
        table_rules.append({"catalog": spec["catalog"], "privileges": _table_public_privs if spec["public"] else []})

    # global default rules go last
    table_rules.append(
        {
            # default table privs can be 'read-only' (i.e. select) or 'no privileges'
            "privileges": (_table_public_privs if dsl["public"] else [])
        }
    )
    schema_rules.append(
        {
            # defaulting all schemas to owner is not safe
            # schemas should be assigned ownership on an explicit basis
            "owner": False
        }
    )
    catalog_rules.append(
        {
            # allows basic 'show schemas' and 'show tables' operations for everyone
            "allow": "read-only"
        }
    )

    # assemble the final json structure and return it
    rules = {"catalogs": catalog_rules, "schemas": schema_rules, "tables": table_rules}
    return rules


def main():
    dsl_fname = sys.argv[1]

    with open(dsl_fname, "r") as dsl_file:
        if dsl_fname.endswith(".json"):
            dsl = json.load(dsl_file)
        elif dsl_fname.endswith(".yaml"):
            dsl = yaml.safe_load(dsl_file)
        else:
            raise ValueError(f"Filename {dsl_fname} had unrecognized suffix")

    rules = dsl_to_rules(dsl, validate=True)

    with sys.stdout as rules_file:
        json.dump(rules, rules_file, indent=4)
        rules_file.write("\n")


if __name__ == "__main__":
    main()
