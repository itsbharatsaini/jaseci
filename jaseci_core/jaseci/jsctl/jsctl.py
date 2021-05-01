"""
Command line tool for Jaseci
"""

import click
import os.path
import pickle
import functools
import json
from inspect import signature

from jaseci.utils.mem_hook import mem_hook
from jaseci.utils.utils import copy_func
from jaseci.master import master as master_class

session = {
    "filename": "js.session",
    "master": master_class(h=mem_hook()),
}


def blank_func():
    pass


@click.group()
@click.option('--filename', '-f', default="js.session")
@click.option('--mem-only', '-m', default=False)
def cli(filename, mem_only):
    """
    Primary entry point for CLI,
    checks for and loads session file
    """
    session['filename'] = filename if not mem_only else None
    if (os.path.isfile(filename)):
        session['master'] = pickle.load(open(filename, 'rb'))


def interface_api(api_name, **kwargs):
    """
    Interfaces Master apis after processing arguments/parameters
    from cli
    """
    if('code' in kwargs):
        if (os.path.isfile(kwargs['code'])):
            with open(kwargs['code'], 'r') as file:
                kwargs['code'] = file.read()
    if('ctx' in kwargs):
        kwargs['ctx'] = json.loads(kwargs['ctx'])
    print(session['master'].general_interface_to_api(kwargs, api_name))
    pickle.dump(session['master'], open(session['filename'], 'wb'))


def extract_api_tree():
    """
    Generates a tree of command group names and function 
    signatures in leaves from API function names in Master
    """
    api_funcs = {}
    for i in dir(session['master']):
        if (i.startswith('api_')):
            # Get function names and signatures
            func_str = i[4:]
            cmd_groups = func_str.split('_')
            func_sig = signature(getattr(session['master'], i))

            # Build hierarchy of command groups
            api_root = api_funcs
            for j in cmd_groups:
                if (j not in api_root.keys()):
                    api_root[j] = {}
                api_root = api_root[j]
            api_root['leaf'] = [i, func_sig]
    return api_funcs


def build_cmd(group_func, func_name, api_name):
    """
    Generates Click function with options for each command
    group and leaf signatures
    """
    f = functools.partial(
        copy_func(interface_api, func_name), api_name=api_name)
    f.__name__ = func_name
    func_sig = session['master'].get_api_signature(api_name)
    for i in func_sig.parameters.keys():
        if(i == 'self'):
            continue
        f = click.option(f'-{i}')(f)
    return group_func.command()(f)


def cmd_tree_builder(location, group_func=cli):
    """
    Generates Click command groups from API tree recursively
    """
    for i in location.keys():
        loc = location[i]
        if ('leaf' in loc):
            build_cmd(group_func, i, loc['leaf'][0])
            continue
        else:
            new_func = group_func.group()(copy_func(blank_func, i))
        cmd_tree_builder(loc, new_func)


def main():
    cmd_tree_builder(extract_api_tree())
    cli()

if __name__ == '__main__':
    main()