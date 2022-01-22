import sys
import os
import json
import argparse
import re

import yaml  # via pyyaml module

import jsonschema

from .dsl2rules import dsl_to_rules
from .__init__ import __version__

_out_of_sync_message = """{prog}: {jsonfile} out of sync with {dslfile}

suggested steps to fix your commit:
$ pip install --user osc-trino-acl-dsl=={version}
$ trino-dsl-to-rules {dslfile} > {jsonfile}
$ git add {jsonfile}
"""

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('paths', metavar='CHECK_FILES', nargs='*',
        help='files to check, normally files staged for git commit')
    parser.add_argument('--check-pattern', metavar='CHECK_PATTERN',
        help='check only files that match this regular expression',
        default='^trino-acl-dsl\.yaml$')

    # parse command line args
    args = parser.parse_args(sys.argv[1:]) # argv[0] is command

    # precompile our regular expression that defines which files to check
    print(f"{parser.prog}: checking files matching regex '{args.check_pattern}'")
    checkre = re.compile(args.check_pattern)

    for pname in args.paths:
        dname, fname = os.path.split(pname)
        if not checkre.match(fname):
            print(f"{parser.prog}: ignoring {pname}")
            continue
        print(f"{parser.prog}: checking {pname}")
        rulespath = os.path.join(dname, "rules.json")
        if not os.path.isfile(rulespath):
            # I expect a rules.json file for any file that matches the pattern
            print(f"{parser.prog}: did not find expected file {rulespath}")
            sys.exit(1)
        print(f"{parser.prog}: checking consistency with {rulespath}")
        try:
            # load the dsl yaml and convert it to rules.json format
            with open(pname, 'r') as dsl_file:
                dsl = yaml.safe_load(dsl_file)
            with open(rulespath, 'r') as json_file:
                jsonrules = json.load(json_file)
            dslrules = dsl_to_rules(dsl, validate = True)
            if not (jsonrules == dslrules):
                print(_out_of_sync_message.format(
                    prog = parser.prog,
                    jsonfile = rulespath,
                    dslfile = pname,
                    version = __version__))
                sys.exit(1)
        except Exception as e:
            # any exception is a test failure
            print(f"{parser.prog}: commit check failed with exception {type(e)}:\n{e}")
            sys.exit(1)
        # all checks passed for current file
        print(f"{parser.prog}: check succeeded for {pname}")
    # all checks passed for any matching files, exit with 'success'
    sys.exit(0)

if __name__ == "__main__":
    main()
