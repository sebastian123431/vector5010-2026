import unittest
import sys
from portafoliosapp.tests import PortfolioViewTests

suite = unittest.defaultTestLoader.loadTestsFromTestCase(PortfolioViewTests)
result = unittest.TextTestRunner(verbosity=2).run(suite)
print('WAS_SUCCESSFUL', result.wasSuccessful())
print('FAIL_COUNT', len(result.failures), 'ERROR_COUNT', len(result.errors))
for test_name, tb in result.failures:
    print('FAIL_TEST', test_name)
    print(tb)
for test_name, tb in result.errors:
    print('ERROR_TEST', test_name)
    print(tb)
sys.exit(0 if result.wasSuccessful() else 1)
