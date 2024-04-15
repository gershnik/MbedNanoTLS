#! /usr/bin/env -S python3 -u

import sys
import shutil
import re
import subprocess
import argparse
import json
import urllib.request

from pathlib import Path
from textwrap import dedent

ROOT = Path(__file__).parent.parent

parser = argparse.ArgumentParser()

parser.add_argument("--tag", dest='tag', type=str, required=True)
parser.add_argument("--config", dest='config', type=Path, required=True)

args = parser.parse_args()


with open(args.config, "rt") as config_json:
    CONFIG_CHANGES = json.load(config_json)


BUILD_DIR = ROOT/'build'


if BUILD_DIR.is_dir():
    shutil.rmtree(BUILD_DIR)


#Step 1: Download code archive into build/sources.tgz

BUILD_DIR.mkdir(parents=True)
tarball_url = f"https://api.github.com/repos/Mbed-TLS/mbedtls/tarball/{args.tag}"
urllib.request.urlretrieve(tarball_url, BUILD_DIR/'sources.tgz')

#Step 2: Unpack archive into build/sources

(BUILD_DIR/'sources').mkdir(parents=True)
subprocess.run(['tar', '-xzf', BUILD_DIR/'sources.tgz', '--strip-components=1'], cwd=BUILD_DIR/'sources', check=True)

#Step 3: Stage headers and sources

DIR_MAPPING = {
    'include/mbedtls':  'mbedtls',
    'include/psa':      'psa',
    'library':          'sources'
}

def filtered_copy(src, dst, *args, follow_symlinks=True):
    if not Path(src).suffix in ('.h', '.c'):
        return
    return shutil.copy2(src, dst, *args, follow_symlinks=follow_symlinks)

(BUILD_DIR/'stage').mkdir(parents=True)
for src, dst in DIR_MAPPING.items():
    shutil.copytree(BUILD_DIR/'sources'/src, BUILD_DIR/'stage'/dst, copy_function=filtered_copy)

#Step 4: Create renaming header

MBDED_FUNC_RE = re.compile(r'^(?:\b\w+\b ?\*?)+ *((?:mbedtls_|psa_)[a-zA-Z_0-9]+)\(', re.MULTILINE | re.ASCII)
MBDED_VAR_RE = re.compile(r'^extern (?:const)? (?:\b\w+\b ?\*?)+((?:mbedtls_|psa_)[a-zA-Z_0-9]+)', re.MULTILINE | re.ASCII)

funcs = set()

for pattern in ('*.h', '*.c'):
    for codefile in (BUILD_DIR/'stage').rglob(pattern):
        content = codefile.read_text("utf-8")
        for match in MBDED_FUNC_RE.finditer(content):
            funcs.add(match.group(1))
        for match in MBDED_VAR_RE.finditer(content):
            funcs.add(match.group(1))

funcs = [func for func in funcs]
funcs.sort()
        
with open(BUILD_DIR/'stage/mbedtls/rename.h', 'wt') as dest:
    dest.write(dedent('''
        //  Copyright 2024 Eugene Gershnik
        //  SPDX-License-Identifier: Apache-2.0
        
        #ifndef HEADER_MBEDTLS_RENAME_H_INCLUDED
        #define HEADER_MBEDTLS_RENAME_H_INCLUDED
                      
        ''').lstrip())
    for name in funcs:
        dest.write(f'#pragma redefine_extname {name} _custom_{name}\n')

    dest.write("\n#endif\n")

#Step 5: Add -O3 build option

common_text = (BUILD_DIR/'stage/sources/common.h').read_text("utf-8")

HEADER_START_RE = re.compile(r'^#ifndef\s+(?P<macro>\w+)\s*\n#define\s+(?P=macro)\s*\n', re.MULTILINE)

match = HEADER_START_RE.search(common_text)
if match is None:
    print("Unable to find common header start", file=sys.stderr)
    sys.exit(1)

common_text = common_text[0:match.end()] + '\n#pragma GCC optimize "O3"\n\n' + common_text[match.end():]

(BUILD_DIR/'stage/sources/common.h').write_text(common_text, "utf-8")

#Step 6: Set up configuration

CONFIG_INCLUDES = '''
#include <platform/inc/platform_mbed.h>
#include "rename.h"

'''

def handleConfigLine(line, setting, value):
    if isinstance(value, bool):
        if value:
            if line.startswith(f'//#define {setting}'):
                lines.append(line[2:])
                return True
        else:
            if line.startswith(f'#define {setting}'):
                lines.append('//'+line)
                return True
    elif isinstance(value, str):
        if line.startswith(f'//#define {setting}'):
            lines.append(line)
            lines.append(f'#define {setting} {value}')
            return True
        if line.startswith(f'#define {setting}'):
            lines.append('//'+line)
            lines.append(f'#define {setting} {value}')
            return True
    return False
        

lines = []
includes_added = False
with open(BUILD_DIR/'stage/mbedtls/mbedtls_config.h', 'rt') as config_text:
    for line in config_text:
        if not includes_added and len(line.strip()) == 0:
            lines.append(CONFIG_INCLUDES)
            includes_added = True
            continue
        handled = False
        for setting, value in CONFIG_CHANGES.items():
            if handleConfigLine(line, setting, value):
                del CONFIG_CHANGES[setting]
                handled = True
                break
        if not handled:
            lines.append(line)

if len(CONFIG_CHANGES) != 0:
    print("Warning: the following config settings were not used: ")
    for setting in CONFIG_CHANGES.keys():
        print(setting)

with open(BUILD_DIR/'stage/mbedtls/mbedtls_config.h', 'wt') as config_text:
    for line in lines:
        config_text.write(line)

#Step 7: Copy stage to main directory

for dir in DIR_MAPPING.values():
    if (ROOT/'src'/dir).is_dir():
        shutil.rmtree(ROOT/'src'/dir)
    (BUILD_DIR/'stage'/dir).rename(ROOT/'src'/dir)