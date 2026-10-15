import os
import unittest
from unittest.mock import patch

from pyhocon import ConfigFactory, ConfigSubstitutionException


class TestOptionalOverrideChain(unittest.TestCase):
    def parse(self, content, environment=None):
        with patch.dict(os.environ, environment or {}, clear=True):
            return ConfigFactory.parse_string(content)

    def test_environment_override_matrix(self):
        content = '''
        app {
            settings {
                label = "123"
                value = "123"
                value = ${?PYHOCON_FIRST_OVERRIDE}
                value = ${?PYHOCON_SECOND_OVERRIDE}
            }
        }
        '''
        cases = [
            ({}, '123'),
            ({'PYHOCON_FIRST_OVERRIDE': 'first-value'}, 'first-value'),
            ({'PYHOCON_SECOND_OVERRIDE': 'second-value'}, 'second-value'),
            ({'PYHOCON_FIRST_OVERRIDE': 'first-value', 'PYHOCON_SECOND_OVERRIDE': 'second-value'}, 'second-value'),
            ({'PYHOCON_FIRST_OVERRIDE': ''}, ''),
            ({'PYHOCON_FIRST_OVERRIDE': 'first-value', 'PYHOCON_SECOND_OVERRIDE': ''}, ''),
        ]
        for environment, expected in cases:
            with self.subTest(environment=environment):
                config = self.parse(content, environment)
                self.assertEqual(config['app.settings.value'], expected)
                self.assertIsInstance(config['app.settings.value'], str)
                self.assertEqual(config['app.settings.label'], '123')

    def test_missing_chain_preserves_default_types(self):
        defaults = [
            ('"default"', 'default'),
            ('""', ''),
            ('0', 0),
            ('false', False),
            ('[]', []),
            ('{}', {}),
            ('[1, 2]', [1, 2]),
            ('{a: 1}', {'a': 1}),
            ('null', None),
        ]
        for literal, expected in defaults:
            with self.subTest(default=literal):
                config = self.parse(
                    'value = ' + literal + '\n'
                    'value = ${?PYHOCON_FIRST_OVERRIDE}\n'
                    'value = ${?PYHOCON_SECOND_OVERRIDE}\n'
                )
                self.assertIn('value', config)
                actual = config['value']
                self.assertEqual(actual, expected)
                if expected is None:
                    self.assertIsNone(actual)
                elif isinstance(expected, (str, bool, int)):
                    self.assertIs(type(actual), type(expected))

    def test_three_missing_overrides_and_reference(self):
        config = self.parse('''
        value = "default"
        value = ${?PYHOCON_FIRST_OVERRIDE}
        value = ${?PYHOCON_SECOND_OVERRIDE}
        value = ${?PYHOCON_FIRST_OVERRIDE}
        result = ${value}
        ''')
        self.assertEqual(config['value'], 'default')
        self.assertEqual(config['result'], 'default')

    def test_present_value_between_missing_overrides(self):
        config = self.parse('''
        value = "default"
        value = ${?PYHOCON_FIRST_OVERRIDE}
        value = ${?PYHOCON_SECOND_OVERRIDE}
        value = ${?PYHOCON_FIRST_OVERRIDE}
        ''', {'PYHOCON_SECOND_OVERRIDE': 'middle-value'})
        self.assertEqual(config['value'], 'middle-value')

    def test_dotted_missing_chain(self):
        config = self.parse('''
        app.settings.value = "default"
        app.settings.value = ${?PYHOCON_FIRST_OVERRIDE}
        app.settings.value = ${?PYHOCON_SECOND_OVERRIDE}
        ''')
        self.assertEqual(config['app.settings.value'], 'default')

    def test_concatenated_text_is_not_discarded(self):
        config = self.parse('''
        value = "default"
        value = ${?PYHOCON_FIRST_OVERRIDE}"suffix"
        value = ${?PYHOCON_SECOND_OVERRIDE}
        ''')
        self.assertEqual(config['value'], 'suffix')
        config = self.parse('''
        value = "default"
        value = "prefix"${?PYHOCON_FIRST_OVERRIDE}${?PYHOCON_SECOND_OVERRIDE}"suffix"
        value = ${?PYHOCON_FIRST_OVERRIDE}
        ''')
        self.assertEqual(config['value'], 'prefixsuffix')

    def test_explicit_null_is_not_replaced_by_older_default(self):
        config = self.parse('''
        value = "default"
        value = null
        value = ${?PYHOCON_FIRST_OVERRIDE}
        value = ${?PYHOCON_SECOND_OVERRIDE}
        ''')
        self.assertIn('value', config)
        self.assertIsNone(config['value'])

    def test_substitution_cycles_still_raise(self):
        with self.assertRaises(ConfigSubstitutionException):
            self.parse('''
            a = ${b}
            b = ${a}
            ''')
