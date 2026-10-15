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
            auth {
                username = "123"
                password = "123"
                password = ${?APP_SERVICE_ACCOUNT_PASSWORD}
                password = ${?OTHER_APP_PASSWORD}
            }
        }
        '''
        cases = [
            ({}, '123'),
            ({'APP_SERVICE_ACCOUNT_PASSWORD': 'password'}, 'password'),
            ({'OTHER_APP_PASSWORD': 'password2'}, 'password2'),
            ({'APP_SERVICE_ACCOUNT_PASSWORD': 'password', 'OTHER_APP_PASSWORD': 'password2'}, 'password2'),
            ({'APP_SERVICE_ACCOUNT_PASSWORD': ''}, ''),
            ({'APP_SERVICE_ACCOUNT_PASSWORD': 'password', 'OTHER_APP_PASSWORD': ''}, ''),
        ]
        for environment, expected in cases:
            with self.subTest(environment=environment):
                config = self.parse(content, environment)
                self.assertEqual(config['app.auth.password'], expected)
                self.assertIsInstance(config['app.auth.password'], str)
                self.assertEqual(config['app.auth.username'], '123')

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
                    'value = ${?APP_SERVICE_ACCOUNT_PASSWORD}\n'
                    'value = ${?OTHER_APP_PASSWORD}\n'
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
        value = ${?APP_SERVICE_ACCOUNT_PASSWORD}
        value = ${?OTHER_APP_PASSWORD}
        value = ${?APP_SERVICE_ACCOUNT_PASSWORD}
        result = ${value}
        ''')
        self.assertEqual(config['value'], 'default')
        self.assertEqual(config['result'], 'default')

    def test_present_value_between_missing_overrides(self):
        config = self.parse('''
        value = "default"
        value = ${?APP_SERVICE_ACCOUNT_PASSWORD}
        value = ${?OTHER_APP_PASSWORD}
        value = ${?APP_SERVICE_ACCOUNT_PASSWORD}
        ''', {'OTHER_APP_PASSWORD': 'middle'})
        self.assertEqual(config['value'], 'middle')

    def test_dotted_missing_chain(self):
        config = self.parse('''
        app.auth.password = "default"
        app.auth.password = ${?APP_SERVICE_ACCOUNT_PASSWORD}
        app.auth.password = ${?OTHER_APP_PASSWORD}
        ''')
        self.assertEqual(config['app.auth.password'], 'default')

    def test_concatenated_text_is_not_discarded(self):
        config = self.parse('''
        value = "default"
        value = ${?APP_SERVICE_ACCOUNT_PASSWORD}"suffix"
        value = ${?OTHER_APP_PASSWORD}
        ''')
        self.assertEqual(config['value'], 'suffix')
        config = self.parse('''
        value = "default"
        value = "prefix"${?APP_SERVICE_ACCOUNT_PASSWORD}${?OTHER_APP_PASSWORD}"suffix"
        value = ${?APP_SERVICE_ACCOUNT_PASSWORD}
        ''')
        self.assertEqual(config['value'], 'prefixsuffix')

    def test_explicit_null_is_not_replaced_by_older_default(self):
        config = self.parse('''
        value = "default"
        value = null
        value = ${?APP_SERVICE_ACCOUNT_PASSWORD}
        value = ${?OTHER_APP_PASSWORD}
        ''')
        self.assertIn('value', config)
        self.assertIsNone(config['value'])

    def test_substitution_cycles_still_raise(self):
        with self.assertRaises(ConfigSubstitutionException):
            self.parse('''
            a = ${b}
            b = ${a}
            ''')
