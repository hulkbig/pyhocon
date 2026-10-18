# -*- encoding: utf-8 -*-
import json

import pytest

from pyhocon import ConfigTree
from pyhocon.converter import HOCONConverter


@pytest.mark.parametrize('key', ['a' + chr(code) + 'b' for code in range(32)] + [r'a\b', r'a\q', 'ordinary', 'café'])
@pytest.mark.parametrize('layout', ['root', 'nested', 'list'])
@pytest.mark.parametrize('compact,indent', [(False, 2), (True, 1), (False, 4)])
def test_json_key_round_trip(key, layout, compact, indent):
    tree = ConfigTree()
    tree.put(key, 1)
    assert list(tree.keys()) == [key]
    expected = {key: 1}
    if layout != 'root':
        parent = ConfigTree()
        parent.put('container', tree if layout == 'nested' else [tree])
        tree = parent
        expected = {'container': expected if layout == 'nested' else [expected]}

    output = HOCONConverter.to_json(tree, compact=compact, indent=indent)

    assert json.loads(output) == expected


@pytest.mark.parametrize('compact,indent', [(False, 2), (True, 1), (False, 4)])
def test_json_unicode_key_format(compact, indent):
    tree = ConfigTree()
    tree.put('café', 'déjà vu')

    output = HOCONConverter.to_json(tree, compact=compact, indent=indent)

    assert output == '{\n' + ' ' * indent + '"café": "déjà vu"\n}'
