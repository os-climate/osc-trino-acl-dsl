# osc-trino-acl-dsl
A declarative format for configuring Trino access control

To operationalize this code you need Trino adminstrator privileges

### example:
The following command:
```sh
python osc_trino_acl_dsl/dsl2rules.py examples/dsl-example-1.json
```

Will produce this output:
```json
{
    "catalogs": [
        {
            "group": "admins",
            "allow": "all"
        },
        {
            "group": ".*",
            "catalog": "dev",
            "allow": "all"
        },
        {
            "group": "workflow_a_dev|workflow_b_dev",
            "catalog": "prod",
            "allow": "all"
        },
        {
            "allow": "read-only"
        }
    ],
    "schemas": [
        {
            "group": "admins",
            "owner": true
        },
        {
            "group": ".*",
            "catalog": "dev",
            "schema": "sandbox",
            "owner": true
        },
        {
            "group": "workflow_a_dev",
            "catalog": "prod",
            "schema": "workflow_a",
            "owner": true
        },
        {
            "group": "workflow_b_dev",
            "catalog": "prod",
            "schema": "workflow_b",
            "owner": true
        },
        {
            "owner": false
        }
    ],
    "tables": [
        {
            "group": "admins",
            "privileges": [
                "SELECT",
                "INSERT",
                "DELETE",
                "OWNERSHIP"
            ]
        },
        {
            "group": "workflow_a_dev",
            "catalog": "prod",
            "schema": "workflow_a",
            "table": "userfacing",
            "privileges": [
                "SELECT",
                "INSERT",
                "DELETE",
                "OWNERSHIP"
            ]
        },
        {
            "group": "workflow_a_quant",
            "catalog": "prod",
            "schema": "workflow_a",
            "table": "userfacing",
            "privileges": [
                "SELECT"
            ],
            "columns": [
                {
                    "name": "dev_a",
                    "allow": false
                }
            ]
        },
        {
            "group": "workflow_a_user",
            "catalog": "prod",
            "schema": "workflow_a",
            "table": "userfacing",
            "privileges": [
                "SELECT"
            ],
            "columns": [
                {
                    "name": "dev_a",
                    "allow": false
                },
                {
                    "name": "quant_a",
                    "allow": false
                }
            ]
        },
        {
            "catalog": "prod",
            "schema": "workflow_a",
            "table": "userfacing",
            "privileges": []
        },
        {
            "group": "workflow_a_dev",
            "catalog": "prod",
            "schema": "workflow_a",
            "table": "backend",
            "privileges": [
                "SELECT",
                "INSERT",
                "DELETE",
                "OWNERSHIP"
            ]
        },
        {
            "catalog": "prod",
            "schema": "workflow_a",
            "table": "backend",
            "privileges": []
        },
        {
            "group": "workflow_b_dev",
            "catalog": "prod",
            "schema": "workflow_b",
            "table": "frontend",
            "privileges": [
                "SELECT",
                "INSERT",
                "DELETE",
                "OWNERSHIP"
            ]
        },
        {
            "group": "workflow_b_quant",
            "catalog": "prod",
            "schema": "workflow_b",
            "table": "frontend",
            "privileges": [
                "SELECT"
            ],
            "filter": "contains(current_groups(), access) or access = 'public'",
            "columns": [
                {
                    "name": "access",
                    "allow": false
                },
                {
                    "name": "dev_b",
                    "allow": false
                }
            ]
        },
        {
            "catalog": "prod",
            "schema": "workflow_b",
            "table": "frontend",
            "privileges": [
                "SELECT"
            ],
            "filter": "contains(current_groups(), access) or access = 'public'",
            "columns": [
                {
                    "name": "access",
                    "allow": false
                },
                {
                    "name": "dev_b",
                    "allow": false
                },
                {
                    "name": "quant_b",
                    "allow": false
                }
            ]
        },
        {
            "group": ".*",
            "catalog": "dev",
            "schema": "sandbox",
            "privileges": [
                "SELECT",
                "INSERT",
                "DELETE",
                "OWNERSHIP"
            ]
        },
        {
            "catalog": "dev",
            "schema": "sandbox",
            "privileges": [
                "SELECT"
            ]
        },
        {
            "group": "workflow_a_dev",
            "catalog": "prod",
            "schema": "workflow_a",
            "privileges": [
                "SELECT",
                "INSERT",
                "DELETE",
                "OWNERSHIP"
            ]
        },
        {
            "catalog": "prod",
            "schema": "workflow_a",
            "privileges": []
        },
        {
            "group": "workflow_b_dev",
            "catalog": "prod",
            "schema": "workflow_b",
            "privileges": [
                "SELECT",
                "INSERT",
                "DELETE",
                "OWNERSHIP"
            ]
        },
        {
            "catalog": "prod",
            "schema": "workflow_b",
            "privileges": [
                "SELECT"
            ]
        },
        {
            "catalog": "dev",
            "privileges": [
                "SELECT"
            ]
        },
        {
            "catalog": "prod",
            "privileges": [
                "SELECT"
            ]
        },
        {
            "privileges": [
                "SELECT"
            ]
        }
    ]
}
```

