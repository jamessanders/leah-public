import unittest
import tempfile
import os
from leah.utils.GlobalFileManager import GlobalFileManager

class DummyConfigManager:
    pass

class TestGlobalFileManager(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.read_root = self.temp_dir.name
        self.write_root = self.temp_dir.name
        self.gfm = GlobalFileManager(DummyConfigManager(), self.read_root, self.write_root)
        self.test_file = os.path.join(self.write_root, 'test.txt')
        with open(self.test_file, 'w', encoding='utf-8') as f:
            f.write('line1\nline2\nline3\nline4')

    def tearDown(self):
        self.temp_dir.cleanup()

    def read_file(self):
        with open(self.test_file, 'r', encoding='utf-8') as f:
            return [line.rstrip('\n') for line in f.readlines()]

    def test_replace_file_lines(self):
        # Replace lines 2-3 with new lines
        result = self.gfm.replace_file_lines(self.test_file, 2, 3, ['new2', 'new3'])
        lines = self.read_file()
        self.assertEqual(lines, ['line1', 'new2', 'new3', 'line4'])
        self.assertIn('replaced the lines 2 to 3', result)

    def test_replace_file_lines_2(self):
        # Replace lines 2-3 with new lines
        result = self.gfm.replace_file_lines(self.test_file, 2, 2, ['new2'])
        lines = self.read_file()
        self.assertEqual(lines, ['line1', 'new2', 'line3', 'line4'])
        self.assertIn('replaced the lines 2 to 2', result)

    def test_insert_file_lines(self):
        # Insert lines under line 2
        result = self.gfm.insert_file_lines(self.test_file, 2, ['inserted2', 'inserted3'])
        lines = self.read_file()
        self.assertEqual(lines, ['line1', 'line2', 'inserted2', 'inserted3', 'line3', 'line4'])
        self.assertIn('inserted the lines', result)

    def test_insert_file_lines_2(self):
        # Insert lines under line 2
        result = self.gfm.insert_file_lines(self.test_file, 3, ['inserted3.5', 'inserted3.6'])
        lines = self.read_file()
        self.assertEqual(lines, ['line1', 'line2', 'line3', 'inserted3.5', 'inserted3.6', 'line4'])
        self.assertIn('inserted the lines', result)

    def test_delete_file_lines(self):
        # Delete lines 1-2 (0-based index)
        self.gfm.delete_file_lines(self.test_file, 1, 3)
        lines = self.read_file()
        self.assertEqual(lines, ['line4'])

    def test_delete_file_lines_2(self):
        # Delete lines 1-2 (0-based index)
        self.gfm.delete_file_lines(self.test_file, 3, 3)
        lines = self.read_file()
        self.assertEqual(lines, ['line1', 'line2', 'line4'])


    def test_get_file_lines(self):
        # Write a file with known lines
        with open(self.test_file, 'w', encoding='utf-8') as f:
            f.write('alpha\nbeta\ngamma\n')
        lines = self.gfm.get_file_lines(self.test_file)
        width = len(str(len(lines)))
        def pad(n):
            return str(n).rjust(width)
        self.assertEqual(lines, [
            f'{pad(1)}: alpha\n',
            f'{pad(2)}: beta\n',
            f'{pad(3)}: gamma\n'
        ])
        # Test with more lines to check padding
        with open(self.test_file, 'w', encoding='utf-8') as f:
            f.write('a\n' * 12)
        lines = self.gfm.get_file_lines(self.test_file)
        width = len(str(len(lines)))
        for idx, line in enumerate(lines):
            expected = f'{str(idx+1).rjust(width)}: a\n'
            self.assertEqual(line, expected)

    def test_get_file_lines_long_file(self):
        # Write a file with 123 lines
        with open(self.test_file, 'w', encoding='utf-8') as f:
            for i in range(1, 124):
                f.write(f"line{i}\n")
        lines = self.gfm.get_file_lines(self.test_file)
        width = len(str(len(lines)))
        for idx, line in enumerate(lines):
            expected = f'{str(idx+1).rjust(width)}: line{idx+1}\n'
            self.assertEqual(line, expected)
        # All line numbers should be width characters wide
        for line in lines:
            self.assertRegex(line, rf'^.{{{width}}}: ')

    def test_get_file_lines_range(self):
        # Write a file with 10 lines
        with open(self.test_file, 'w', encoding='utf-8') as f:
            for i in range(1, 11):
                f.write(f"line{i}\n")
        # Get lines 3 to 7 (inclusive)
        start, end = 3, 7
        lines = self.gfm.get_file_lines(self.test_file, start_line_number=start, end_line_number=end)
        width = len(str(len(lines)))
        for idx, line in enumerate(lines):
            expected = f'{str(idx+1).rjust(width)}: line{start+idx}\n'
            self.assertEqual(line, expected)
        # Check that the number of lines is correct
        self.assertEqual(len(lines), end - start + 1)

if __name__ == '__main__':
    unittest.main() 