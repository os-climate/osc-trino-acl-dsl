import pathlib

from setuptools import find_packages, setup

# The directory containing this file
HERE = pathlib.Path(__file__).resolve().parent

# The text of the README file is used as a description
README = (HERE / "README.md").read_text()

# This is a hack to allow single point of definition for __version__
# that is usable by setup.py and also by the package code itself.
# Essentially python has no clean and standardized way to do this.
# importlib.metadata could also work in the other direction but it
# is not consistently defined prior to py 3.8
# In the future when we can safely assume py >= 3.8 this may be a
# more standardized solution.
_about = {}
with open(HERE / "osc_trino_acl_dsl" / "__about__.py") as fp:
    exec(fp.read(), _about)

setup(
    name="osc-trino-acl-dsl",
    version=_about["__version__"],
    description="A DSL for generating rules.json files for Trino",
    long_description=README,
    long_description_content_type="text/markdown",
    url="https://github.com/os-climate/osc-trino-acl-dsl",
    author="OS-Climate",
    author_email="eje@redhat.com",
    license="Apache-2.0",
    classifiers=[
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3 :: Only",
    ],
    packages=find_packages(),
    include_package_data=True,
    package_data={
        # also requires corresponding entry in MANIFEST.in to work with dist
        "osc_trino_acl_dsl": ["jsonschema/*.json"],
    },
    install_requires=["jsonschema", "pyyaml"],
    entry_points={
        "console_scripts": [
            "trino-dsl-to-rules=osc_trino_acl_dsl.dsl2rules:main",
            "trino-acl-dsl-check=osc_trino_acl_dsl.rules_precommit_check:main",
        ],
    },
)
