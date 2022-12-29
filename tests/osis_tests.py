import unittest
import subprocess
import re
import os

class TestOsisGeneration(unittest.TestCase):
    
    # run u2o.py 
    # test osis file is created in output directory
    # There is no mention of \id markers in stdout
    def test_osis_file_is_created(self):
        result = subprocess.run(['python', 'u2o.py', 'TESTID', 'tests/test_data/1cor.usfm'], stdout=subprocess.PIPE)
        file_path = 'output/TESTID.osis'
        self.assertTrue(os.path.exists(file_path))
        self.assertEqual(result.stdout.decode(), '')
        self.assertNotRegex(result.stdout.decode(), re.escape('\id'))        


if __name__ == '__main__':
    unittest.main()