"""
Pruebas unitarias para ASTSecurityValidator en VECTOR 2026.
"""

import unittest
from vectorapp.security.ast_validator import ASTSecurityValidator
from vectorapp.security.permissions import ToolPermissions

class TestASTSecurityValidator(unittest.TestCase):
    def setUp(self):
        self.validator_default = ASTSecurityValidator()

    def test_safe_math_code_passes(self):
        code = """
import math

def execute_tool(action="calculate", **kwargs):
    x = kwargs.get('x', 0)
    return math.sqrt(x) + 10
"""
        result = self.validator_default.validate_code(code)
        self.assertTrue(result['syntax_valid'])
        self.assertTrue(result['security_valid'])
        self.assertEqual(result['risk_level'], 'none')
        self.assertEqual(len(result['violations']), 0)

    def test_blocks_eval(self):
        code = "res = eval('2 + 2')"
        result = self.validator_default.validate_code(code)
        self.assertFalse(result['security_valid'])
        self.assertEqual(result['risk_level'], 'critical')
        symbols = [v['symbol'] for v in result['violations']]
        self.assertIn('eval', symbols)

    def test_blocks_exec(self):
        code = "exec('import os')"
        result = self.validator_default.validate_code(code)
        self.assertFalse(result['security_valid'])
        self.assertEqual(result['risk_level'], 'critical')
        symbols = [v['symbol'] for v in result['violations']]
        self.assertIn('exec', symbols)

    def test_blocks_os_system(self):
        code = """
import os
def execute_tool():
    os.system('dir')
"""
        result = self.validator_default.validate_code(code)
        self.assertFalse(result['security_valid'])
        self.assertEqual(result['risk_level'], 'critical')
        symbols = [v['symbol'] for v in result['violations']]
        self.assertTrue(any('os.system' in s for s in symbols))

    def test_blocks_subprocess(self):
        code = """
import subprocess
def execute_tool():
    subprocess.Popen(['notepad.exe'])
"""
        result = self.validator_default.validate_code(code)
        self.assertFalse(result['security_valid'])
        rules = [v['rule'] for v in result['violations']]
        self.assertIn('FORBIDDEN_IMPORT', rules)

    def test_blocks_ctypes_socket_multiprocessing(self):
        modules = ['ctypes', 'socket', 'multiprocessing', 'winreg']
        for mod in modules:
            code = f"import {mod}\ndef execute_tool(): pass"
            result = self.validator_default.validate_code(code)
            self.assertFalse(result['security_valid'], f"Debería bloquear {mod}")
            self.assertEqual(result['risk_level'], 'critical')

    def test_blocks_sandbox_escape_attributes(self):
        escapes = [
            "x = ().__class__.__bases__[0].__subclasses__()",
            "f = getattr(foo, '__globals__')",
            "c = (lambda: None).__code__"
        ]
        for esc in escapes:
            result = self.validator_default.validate_code(esc)
            self.assertFalse(result['security_valid'], f"Debería bloquear escape: {esc}")
            rules = [v['rule'] for v in result['violations']]
            self.assertIn('SANDBOX_ESCAPE_ATTEMPT', rules)

    def test_blocks_open_without_filesystem_permission(self):
        code = "with open('archivo.txt', 'r') as f: content = f.read()"
        # Permisos default no tienen filesystem_read
        result = self.validator_default.validate_code(code)
        self.assertFalse(result['security_valid'])
        symbols = [v['symbol'] for v in result['violations']]
        self.assertIn('open', symbols)

    def test_allows_open_with_filesystem_permission(self):
        code = "with open('archivo.txt', 'r') as f: content = f.read()"
        perms = ToolPermissions(filesystem_read=True)
        val = ASTSecurityValidator(permissions=perms)
        result = val.validate_code(code)
        self.assertTrue(result['security_valid'])

    def test_blocks_network_without_network_permission(self):
        code = "import requests\nres = requests.get('https://example.com')"
        result = self.validator_default.validate_code(code)
        self.assertFalse(result['security_valid'])
        rules = [v['rule'] for v in result['violations']]
        self.assertIn('DISALLOWED_IMPORT', rules)

    def test_allows_network_with_network_permission(self):
        code = "import requests\ndef execute_tool(): pass"
        perms = ToolPermissions(network=True)
        val = ASTSecurityValidator(permissions=perms)
        result = val.validate_code(code)
        self.assertTrue(result['security_valid'])

if __name__ == '__main__':
    unittest.main()
