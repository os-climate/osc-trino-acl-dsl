import re

from osc_trino_acl_dsl.dsl2rules import dsl_to_rules


class Table(object):
    def __init__(self, catalog: str, schema: str, table: str):
        self.catalog: str = str(catalog)
        self.schema: str = str(schema)
        self.table: str = str(table)


class User(object):
    def __init__(self, user: str, group):
        self.user = str(user)
        if type(group) == set:
            self.groups = set([str(e) for e in list(group)])
        elif type(group) == list:
            self.groups = set([str(e) for e in group])
        else:
            self.groups = set([str(group)])


def rule_matches(rule: dict, table: Table, user: User) -> bool:
    """emulates trino rule matching semantics"""
    if ("catalog" in rule) and (not re.fullmatch(rule["catalog"], table.catalog)):
        return False
    if ("schema" in rule) and (not re.fullmatch(rule["schema"], table.schema)):
        return False
    if ("table" in rule) and (not re.fullmatch(rule["table"], table.table)):
        return False
    if ("user" in rule) and (not re.fullmatch(rule["user"], user.user)):
        return False
    if "group" in rule:
        x = [e for e in list(user.groups) if re.fullmatch(rule["group"], e)]
        if len(x) == 0:
            return False
    return True


def first_matching_rule(user: User, table: Table, rules: list) -> dict:
    for rule in rules:
        if rule_matches(rule, table, user):
            return rule
    return None


def rule_permissions(user: User, table: Table, rules: dict) -> tuple:
    assert type(rules) == dict
    assert "catalogs" in rules
    assert "schemas" in rules
    assert "tables" in rules

    crule = first_matching_rule(user, table, rules["catalogs"])
    assert type(crule) == dict
    assert "allow" in crule
    allow = crule["allow"]

    srule = first_matching_rule(user, table, rules["schemas"])
    assert type(srule) == dict
    assert "owner" in srule
    owner = srule["owner"]

    trule = first_matching_rule(user, table, rules["tables"])
    assert type(trule) == dict
    assert "privileges" in trule
    privs = trule["privileges"]

    return (allow, owner, privs)


_table_admin_privs = ["SELECT", "INSERT", "DELETE", "OWNERSHIP"]
_table_public_privs = ["SELECT"]


def test_dsl_minimal():
    # a minimal schema: declares one admin group, defaults public, and no other rules
    dsl = {"admin": [{"group": "admins"}], "public": True, "catalogs": [], "schemas": [], "tables": []}
    rules = dsl_to_rules(dsl, validate=True)

    # test permissions of the admin group
    allow, owner, privs = rule_permissions(User("x", "admins"), Table("x", "x", "x"), rules)
    assert allow == "all"
    assert owner is True
    assert privs == _table_admin_privs

    # test permissions of generic user
    allow, owner, privs = rule_permissions(User("x", []), Table("x", "x", "x"), rules)
    assert allow == "read-only"
    assert owner is False
    assert privs == _table_public_privs


def test_dsl_catalog():
    admin1 = {"group": "admins"}
    cat1 = {"catalog": "dev", "public": False}
    dsl = {"admin": [admin1], "public": True, "catalogs": [cat1], "schemas": [], "tables": []}
    rules = dsl_to_rules(dsl, validate=True)

    # test permissions of the admin group
    allow, owner, privs = rule_permissions(User("x", "admins"), Table("x", "x", "x"), rules)
    assert allow == "all"
    assert owner is True
    assert privs == _table_admin_privs

    # test permissions of generic user and non-dev catalog (global default)
    allow, owner, privs = rule_permissions(User("x", []), Table("x", "x", "x"), rules)
    assert allow == "read-only"
    assert owner is False
    assert privs == _table_public_privs

    allow, owner, privs = rule_permissions(User("x", []), Table("dev", "x", "x"), rules)
    assert allow == "read-only"
    assert owner is False
    assert privs == []


def test_dsl_schema():
    admin1 = {"group": "admins"}
    devs = {"group": "devs"}
    usery = {"user": "usery"}
    cat1 = {"catalog": "dev", "public": False}
    schema1 = {"catalog": "dev", "schema": "proj1", "admin": [devs, usery], "public": True}
    dsl = {"admin": [admin1], "public": True, "catalogs": [cat1], "schemas": [schema1], "tables": []}
    rules = dsl_to_rules(dsl, validate=True)

    # test permissions of the admin group
    allow, owner, privs = rule_permissions(User("x", "admins"), Table("x", "x", "x"), rules)
    assert allow == "all"
    assert owner is True
    assert privs == _table_admin_privs

    # test permissions of generic user and non-dev catalog (global default)
    allow, owner, privs = rule_permissions(User("x", []), Table("x", "x", "x"), rules)
    assert allow == "read-only"
    assert owner is False
    assert privs == _table_public_privs

    # test permissions of the dev group on the dev catalog
    allow, owner, privs = rule_permissions(User("x", "devs"), Table("dev", "x", "x"), rules)
    assert allow == "all"
    assert owner is False
    assert privs == []

    # devs have admin in proj1 schema for all tables
    allow, owner, privs = rule_permissions(User("x", "devs"), Table("dev", "proj1", "x"), rules)
    assert allow == "all"
    assert owner is True
    assert privs == _table_admin_privs

    allow, owner, privs = rule_permissions(User("usery", []), Table("dev", "proj1", "x"), rules)
    assert allow == "all"
    assert owner is True
    assert privs == _table_admin_privs

    # dev-catalog default is non-public (no privs)
    allow, owner, privs = rule_permissions(User("x", "nondev"), Table("dev", "x", "x"), rules)
    assert allow == "read-only"
    assert owner is False
    assert privs == []

    # inside dev.proj1 schema tables default to public
    allow, owner, privs = rule_permissions(User("x", []), Table("dev", "proj1", "x"), rules)
    assert allow == "read-only"
    assert owner is False
    assert privs == _table_public_privs
