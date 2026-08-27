"""Shared markers and fixtures for the treegrid test modules.

The sentinel strings are load-bearing: they are the exact source text of the shared factory,
the per-card init call, and one rule of the shared stylesheet, and several modules count them
to prove the shared half lands once per page. One home means a change to the factory line in
_treegrid_script.html is one edit here, not a hunt across modules.
"""

FACTORY = 'window._treegridInit = window._treegridInit || function(CFG)'
INIT_CALL = 'window._treegridInit(cfg);'
STYLE_RULE = '.fancytree-ext-table tbody td.treegrid-menu-cell'

SIMPLE_COLUMNS = [{'title': 'Name', 'field': 'title'}, {'title': 'Code', 'field': 'code'}]


def simple_nodes(prefix):
    """Three flat rows keyed and coded by prefix -- enough grid for an emission test."""
    return [{'title': f'{prefix} {i}', 'key': f'{prefix}_{i}',
             'data': {'code': f'{prefix}-{i}'}} for i in range(3)]
