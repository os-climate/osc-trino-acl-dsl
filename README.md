# osc-trino-acl-dsl
A declarative format for configuring Trino access control

To operationalize this code you need Trino adminstrator privileges

### example:
```sh
# install package using pipenv, pip or similar tools
$ pipenv install osc-trino-acl-dsl

# the package command `trino-dsl-to-rules` will load the given yaml or json file
# and write the resulting 'rules.json' file to standard output
# dsl-example-1.yaml is in the 'examples' directory of this repository
$ pipenv run trino-dsl-to-rules dsl-example-1.yaml > rules.json

# rules.json is trino file-based access control rules file
$ head rules.json
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
```
