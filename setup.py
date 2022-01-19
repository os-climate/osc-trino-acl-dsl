import pathlib

from setuptools import setup, find_packages

# The directory containing this file
HERE = pathlib.Path(__file__).resolve().parent

# The text of the README file is used as a description
README = (HERE / "README.md").read_text()

setup(
    name = "osc-trino-acl-dsl",
    version = "0.1.0",
    description = "A DSL for generating rules.json files for Trino",
    long_description = README,
    long_description_content_type = "text/markdown",
    url = "https://github.com/os-climate/osc-trino-acl-dsl",
    author = "OS-Climate",
    author_email = "eje@redhat.com",
    license = "Apache-2.0",
    classifiers = [
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3 :: Only",
    ],
    packages = find_packages(),
    include_package_data = True,
    install_requires = [],
    entry_points = {
        "console_scripts": [
            "trino-dsl-to-rules=osc_trino_acl_dsl.dsl2rules:main",
        ],
    },
)
