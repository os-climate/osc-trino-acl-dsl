import argparse
import json
import os
import sys

import yaml  # via pyyaml module

from .__init__ import __version__
from .dsl2rules import dsl_to_rules

_out_of_sync_message = """
{prog}: {jsonfile} out of sync with {dslfile}

suggested steps to fix your commit:
$ pip install --user --upgrade osc-trino-acl-dsl=={version}
$ trino-dsl-to-rules {dslfile} > {jsonfile}
$ git add {jsonfile}
"""

_unchecked_rules_message = """
{prog}: Found modified rules.json files with no corresponding DSL edits:
{flist}

For rules.json managed by DSL, suggested steps to fix:
$ pip install --user --upgrade osc-trino-acl-dsl=={version}
# <make your edits to dsl yaml file>
$ trino-dsl-to-rules path/to/<dsl>.yaml > path/to/rules.json
$ git add path/to/<dsl>.yaml path/to/rules.json

If any of these rules.json files are NOT being managed by a DSL file,
you can fix this by adding an entry to the 'exclude' attribute for this hook
in your .pre-commit-config.yaml, so this check ignores any unmanaged rules.json files
see: https://pre-commit.com/#config-exclude
"""


def check_dsl_rules_consistency(dslpath, rulespath, prog):
    try:
        with open(dslpath, "r") as dsl_file:
            dsl = yaml.safe_load(dsl_file)
        with open(rulespath, "r") as json_file:
            jsonrules = json.load(json_file)
        dslrules = dsl_to_rules(dsl, validate=True)
        if not (jsonrules == dslrules):
            print(_out_of_sync_message.format(prog=prog, jsonfile=rulespath, dslfile=dslpath, version=__version__))
            sys.exit(1)
    except Exception as e:
        # any exception is a test failure
        print(f"{prog}: commit check failed with exception {type(e)}:\n{e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "paths", metavar="CHECK_FILES", nargs="*", help="files to check, normally files staged for git commit"
    )

    # parse command line args
    args = parser.parse_args(sys.argv[1:])  # argv[0] is command

    # I am assuming the `files` attribute in .pre-commit-hooks.yaml
    # (or override in  .pre-commit-config.yaml) is properly set to
    # pass only the expected DSL and rules.json files.
    unchecked_rules_json = set([p for p in args.paths if p.endswith(".json")])
    dsl_yaml = [p for p in args.paths if p.endswith(".yaml")]

    # from the above, notice that I'm taking advantage of the fact that
    # yaml is the DSL, and json is the trino rules.  If either of those
    # conventions ever changes, I'll need some other convention so that I
    # can reliably separate one from the other.

    # It is also possible to make the 'files' regex very path-specific
    # so you could configure one preconfig check for each dsl/rules pair
    # and each matches exactly one pair in your repo

    # useful diagnostic, in the event of a check failure
    print("{prog}: staged DSL files:\n{flist}\n".format(prog=parser.prog, flist="\n".join(dsl_yaml)))
    print("{prog}: staged rule files:\n{flist}\n".format(prog=parser.prog, flist="\n".join(unchecked_rules_json)))

    for dslpath in dsl_yaml:
        print(f"{parser.prog}: checking {dslpath}")
        dname, fname = os.path.split(dslpath)
        rulespath = os.path.join(dname, "rules.json")
        if not os.path.isfile(rulespath):
            # I expect a rules.json file for any file that matches the pattern
            print(f"{parser.prog}: did not find expected file {rulespath}")
            sys.exit(1)
        print(f"{parser.prog}: checking consistency with {rulespath}")
        check_dsl_rules_consistency(dslpath, rulespath, parser.prog)
        # all checks passed for current file
        print(f"{parser.prog}: check succeeded for {dslpath}")
        # we validated a DSL -> rules.json pair, so I can check-off the rules file
        unchecked_rules_json.remove(rulespath)

    # If there are any remaining unchecked rules.json files,
    # there are multiple possibilites:
    # 1) there is an "unmanaged" rules.json file (not using DSL)
    # case (1) will cause this check to fail, but is not technically an error:
    # case (1) should be addressed by using 'exclude' in .pre-commit-config.yaml
    # 2) the user edited a managed rules.json file instead of the DSL: This case
    # is an error and should cause the precommit check to fail.
    # 3) a new version of osc-trino-acl-dsl package was run: in this case the
    # DSL may not have changed, but the rules.json did due to new version

    # check case (3) first
    # this check assumes a companion DSL file named "trino-acl-dsl.yaml"
    # I am not currently sure if there are better possible policies besides
    # making this assumption, or even if better policies are really necessary.
    tmprules = list(unchecked_rules_json)
    for rulespath in tmprules:
        print(f"{parser.prog}: checking rules file {rulespath}")
        dname, fname = os.path.split(rulespath)
        dslpath = os.path.join(dname, "trino-acl-dsl.yaml")
        if not os.path.isfile(dslpath):
            # I have not so far made the file name "trino-acl-dsl.yaml" an official assumption
            # I'm not going to treat this as a check failure
            print(f"{parser.prog}: did not find {dslpath}, skipping")
        else:
            check_dsl_rules_consistency(dslpath, rulespath, parser.prog)
            print(f"{parser.prog}: check succeeded for {dslpath}")
            unchecked_rules_json.remove(rulespath)

    if len(unchecked_rules_json) > 0:
        # any remaining rules files are a potential error so fail the check
        print(
            _unchecked_rules_message.format(
                prog=parser.prog, flist="\n".join(unchecked_rules_json), version=__version__
            )
        )
        sys.exit(1)

    # all checks passed for any matching files, exit with 'success'
    print(f"{parser.prog}: all files passed")
    sys.exit(0)


if __name__ == "__main__":
    main()
