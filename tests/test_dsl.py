import re
import textwrap

import yaml

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


_admin = ["SELECT", "INSERT", "DELETE", "OWNERSHIP"]
_public = ["SELECT"]


def test_dsl_minimal():
    # a minimal schema: declares one admin group, defaults public, and no other rules
    dsl = yaml.load(
        textwrap.dedent("""
            admin:
            - group: admins
            public: true
            catalogs: []
            schemas: []
            tables: []
            """),
        yaml.SafeLoader,
    )
    rules = dsl_to_rules(dsl, validate=True)

    # test permissions of the admin group
    perms = rule_permissions(User("x", "admins"), Table("x", "x", "x"), rules)
    assert perms == ("all", True, _admin)

    # test permissions of generic user
    perms = rule_permissions(User("x", []), Table("x", "x", "x"), rules)
    assert perms == ("read-only", False, _public)


def test_dsl_catalog():
    dsl = yaml.load(
        textwrap.dedent("""
            admin:
            - group: admins
            public: true
            catalogs:
            - catalog: dev
              public: false
            schemas: []
            tables: []
            """),
        yaml.SafeLoader,
    )
    rules = dsl_to_rules(dsl, validate=True)

    # test permissions of the admin group
    perms = rule_permissions(User("x", "admins"), Table("x", "x", "x"), rules)
    assert perms == ("all", True, _admin)

    # test permissions of generic user and non-dev catalog (global default)
    perms = rule_permissions(User("x", []), Table("x", "x", "x"), rules)
    assert perms == ("read-only", False, _public)

    perms = rule_permissions(User("x", []), Table("dev", "x", "x"), rules)
    assert perms == ("read-only", False, [])


def test_dsl_schema():
    dsl = yaml.load(
        textwrap.dedent("""
            admin:
            - group: admins
            public: true
            catalogs:
            - catalog: dev
              public: false
            schemas:
            - catalog: dev
              schema: proj1
              admin:
              - group: devs
              - user: usery
              public: true
            tables: []
            """),
        yaml.SafeLoader,
    )
    rules = dsl_to_rules(dsl, validate=True)

    # test permissions of the admin group
    perms = rule_permissions(User("x", "admins"), Table("x", "x", "x"), rules)
    assert perms == ("all", True, _admin)

    # test permissions of generic user and non-dev catalog (global default)
    perms = rule_permissions(User("x", []), Table("x", "x", "x"), rules)
    assert perms == ("read-only", False, _public)

    # test permissions of the dev group on the dev catalog
    perms = rule_permissions(User("x", "devs"), Table("dev", "x", "x"), rules)
    assert perms == ("all", False, [])

    # devs have admin in proj1 schema for all tables
    perms = rule_permissions(User("x", "devs"), Table("dev", "proj1", "x"), rules)
    assert perms == ("all", True, _admin)

    perms = rule_permissions(User("usery", []), Table("dev", "proj1", "x"), rules)
    assert perms == ("all", True, _admin)

    # dev-catalog default is non-public (no privs)
    perms = rule_permissions(User("x", "nondev"), Table("dev", "x", "x"), rules)
    assert perms == ("read-only", False, [])

    # inside dev.proj1 schema tables default to public
    perms = rule_permissions(User("x", []), Table("dev", "proj1", "x"), rules)
    assert perms == ("read-only", False, _public)


def test_dsl_table():
    dsl = yaml.load(
        textwrap.dedent("""
            admin:
            - group: admins
            public: true
            catalogs:
            - catalog: dev
              public: false
            schemas:
            - catalog: dev
              schema: proj1
              admin:
              - group: devs
              - user: usery
              public: true
            tables:
            - catalog: dev
              schema: proj1
              table: priv1
              admin:
              - user: userz
              public: false
            """),
        yaml.SafeLoader,
    )
    rules = dsl_to_rules(dsl, validate=True)

    # test permissions of the admin group
    perms = rule_permissions(User("x", "admins"), Table("x", "x", "x"), rules)
    assert perms == ("all", True, _admin)

    # global default should be readable
    perms = rule_permissions(User("x", []), Table("x", "x", "x"), rules)
    assert perms == ("read-only", False, _public)

    # dev catalog default should be non-public
    perms = rule_permissions(User("x", []), Table("dev", "x", "x"), rules)
    assert perms == ("read-only", False, [])

    # dev.proj1 schema default should be readable
    perms = rule_permissions(User("x", []), Table("dev", "proj1", "x"), rules)
    assert perms == ("read-only", False, _public)

    # dev.proj1.priv1 should default to non-public
    perms = rule_permissions(User("x", []), Table("dev", "proj1", "priv1"), rules)
    assert perms == ("read-only", False, [])

    # "usery" and "devs" group have schema admin:
    perms = rule_permissions(User("x", "devs"), Table("dev", "proj1", "x"), rules)
    assert perms == ("all", True, _admin)
    perms = rule_permissions(User("usery", []), Table("dev", "proj1", "x"), rules)
    assert perms == ("all", True, _admin)

    # userz added as table admin for priv1
    perms = rule_permissions(User("userz", []), Table("dev", "proj1", "priv1"), rules)
    assert perms == ("all", False, _admin)

    # but userz is not admin for any other table in proj1
    perms = rule_permissions(User("userz", []), Table("dev", "proj1", "x"), rules)
    assert perms == ("all", False, _public)


def test_dsl_table_acl():
    dsl = yaml.load(
        textwrap.dedent("""
            admin:
            - group: admins
            public: true
            catalogs:
            - catalog: dev
              public: false
            schemas:
            - catalog: dev
              schema: proj1
              admin:
              - group: devs
              - user: usery
              public: true
            tables:
            - catalog: dev
              schema: proj1
              table: priv1
              public:
                filter:
                - "population < 1000"
                hide:
                - column3
              acl:
              - id:
                - user: usera
                - user: userb
                filter:
                - "country = 'london'"
                - "year < 2061"
                hide:
                - column1
                - column2
            """),
        yaml.SafeLoader,
    )
    rules = dsl_to_rules(dsl, validate=True)

    # test permissions of the admin group
    perms = rule_permissions(User("x", "admins"), Table("x", "x", "x"), rules)
    assert perms == ("all", True, _admin)

    # global default should be readable
    perms = rule_permissions(User("x", []), Table("x", "x", "x"), rules)
    assert perms == ("read-only", False, _public)

    # dev catalog default should be non-public
    perms = rule_permissions(User("x", []), Table("dev", "x", "x"), rules)
    assert perms == ("read-only", False, [])

    # dev.proj1 schema default should be readable
    perms = rule_permissions(User("x", []), Table("dev", "proj1", "x"), rules)
    assert perms == ("read-only", False, _public)

    # "usery" and "devs" group have schema admin:
    perms = rule_permissions(User("x", "devs"), Table("dev", "proj1", "x"), rules)
    assert perms == ("all", True, _admin)
    perms = rule_permissions(User("usery", []), Table("dev", "proj1", "x"), rules)
    assert perms == ("all", True, _admin)

    for u in ["usera", "userb"]:
        perms = rule_permissions(User(u, []), Table("dev", "proj1", "priv1"), rules)
        assert perms == ("read-only", False, _public)
        r = first_matching_rule(User(u, []), Table("dev", "proj1", "priv1"), rules["tables"])
        assert "filter" in r
        assert r["filter"] == "(country = 'london') and (year < 2061)"
        assert "columns" in r
        assert r["columns"] == [{"name": "column1", "allow": False}, {"name": "column2", "allow": False}]

    # dev.proj1.priv1 should default to public
    # but with additional row and column acl settings
    perms = rule_permissions(User("x", []), Table("dev", "proj1", "priv1"), rules)
    assert perms == ("read-only", False, _public)
    r = first_matching_rule(User("x", []), Table("dev", "proj1", "priv1"), rules["tables"])
    assert "filter" in r
    assert r["filter"] == "(country = 'london') and (population < 1000) and (year < 2061)"
    assert "columns" in r
    assert r["columns"] == [
        {"name": "column1", "allow": False},
        {"name": "column2", "allow": False},
        {"name": "column3", "allow": False},
    ]
