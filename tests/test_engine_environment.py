"""Renderer dependency discovery must work on both desktop and cloud hosts."""
from tests import _guard  # noqa: F401
import os
import subprocess
import unittest
from unittest.mock import patch
from director.studio.engine import _env


class TestRendererEnvironment(unittest.TestCase):
    def environment(self, variables, npm=None, cloud=False):
        result = subprocess.CompletedProcess([], 0, '/global/modules\n', '')
        with patch.dict(os.environ, variables, clear=True), \
             patch('director.studio.engine.subprocess.run', **({'side_effect': npm} if isinstance(npm, Exception) else {'return_value': npm or result})), \
             patch('director.studio.engine.Path.is_dir', return_value=cloud):
            return _env()

    def test_desktop_uses_playwright_default_browser_cache(self):
        self.assertNotIn('PLAYWRIGHT_BROWSERS_PATH', self.environment({}))

    def test_custom_paths_are_preserved(self):
        env = self.environment({'NODE_PATH': '/custom/modules', 'PLAYWRIGHT_BROWSERS_PATH': '/custom/browsers'}, cloud=True)
        self.assertEqual(env['PLAYWRIGHT_BROWSERS_PATH'], '/custom/browsers')
        self.assertEqual(env['NODE_PATH'].split(os.pathsep)[0], '/custom/modules')
        self.assertIn('/global/modules', env['NODE_PATH'].split(os.pathsep))

    def test_cloud_browser_cache_is_retained(self):
        self.assertEqual(self.environment({}, cloud=True)['PLAYWRIGHT_BROWSERS_PATH'], '/opt/pw-browsers')

    def test_npm_optional_when_dependencies_are_already_available(self):
        for error in (FileNotFoundError(), subprocess.TimeoutExpired('npm', 10)):
            with self.subTest(error=type(error).__name__):
                self.assertEqual(self.environment({'NODE_PATH': '/local/modules'}, npm=error)['NODE_PATH'], '/local/modules')

    def test_failed_npm_does_not_add_error_output_to_paths(self):
        env = self.environment({}, npm=subprocess.CompletedProcess([], 1, 'error text', 'failure'))
        self.assertNotIn('NODE_PATH', env)

    def test_paid_credentials_are_not_forwarded(self):
        keys = ('ELEVENLABS_API_KEY', 'FAL_KEY', 'HIGGSFIELD_API_KEY')
        env = self.environment(dict.fromkeys(keys, 'test-only'))
        self.assertFalse(set(keys) & env.keys())
