"""
Pruebas unitarias para ToolPermissions en VECTOR 2026.
"""

import unittest
from vectorapp.security.permissions import ToolPermissions

class TestToolPermissions(unittest.TestCase):
    def test_default_permissions_all_false(self):
        perms = ToolPermissions()
        self.assertFalse(perms.filesystem_read)
        self.assertFalse(perms.filesystem_write)
        self.assertFalse(perms.network)
        self.assertFalse(perms.database)
        self.assertFalse(perms.system_info)

    def test_serialization_roundtrip(self):
        perms = ToolPermissions(filesystem_read=True, network=True)
        d = perms.to_dict()
        restored = ToolPermissions.from_dict(d)
        self.assertEqual(perms, restored)

    def test_infer_category_math(self):
        perms = ToolPermissions.default_for_category("calculations")
        self.assertFalse(perms.filesystem_read)
        self.assertFalse(perms.network)

    def test_infer_category_files(self):
        perms = ToolPermissions.default_for_category("file_operations")
        self.assertTrue(perms.filesystem_read)
        self.assertTrue(perms.filesystem_write)
        self.assertFalse(perms.network)

    def test_infer_category_web(self):
        perms = ToolPermissions.default_for_category("web_scraping")
        self.assertTrue(perms.network)
        self.assertFalse(perms.filesystem_read)
        self.assertFalse(perms.filesystem_write)

    def test_infer_category_database(self):
        perms = ToolPermissions.default_for_category("database")
        self.assertTrue(perms.database)
        self.assertFalse(perms.network)
        self.assertFalse(perms.filesystem_write)

if __name__ == '__main__':
    unittest.main()
