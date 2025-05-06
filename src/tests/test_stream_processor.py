import unittest
from StreamProcessor import StreamProcessor

class TestStreamProcessor(unittest.TestCase):
    def setUp(self):
        self.processor = StreamProcessor('<think>', '</think>')
        self.json_processor = StreamProcessor("```json", "```")
        self.tool_processor = StreamProcessor("```tool_code", "```")
    def test_process_character_no_tags(self):
        result = ''.join([self.processor.process_character(c) for c in 'Hello World'])
        self.assertEqual(result, 'Hello World')
        self.assertEqual(self.processor.matches, [])

    def test_process_character_with_tags(self):
        result = ''.join([self.processor.process_character(c) for c in 'Hello <think>World</think>!'])
        self.assertEqual(result, 'Hello !')
        self.assertEqual(self.processor.matches, ['World'])

    def test_process_character_incomplete_tag(self):
        result = ''.join([self.processor.process_character(c) for c in 'Hello <thinkWorld'])
        self.assertEqual(result, 'Hello <thinkWorld')
        self.assertEqual(self.processor.matches, [])

    def test_process_character_json_tags(self):
        result = ''.join([self.json_processor.process_character(c) for c in 'Data ```json\n\n{"key": "value"}\n\n``` more data'])
        self.assertEqual(result, 'Data  more data')
        self.assertEqual(self.json_processor.matches, ['{"key": "value"}'])

    def test_process_chunk(self):
        result = self.processor.process_chunk('Hello <think>World</think>! Data more data <think>Testing...</think> test')
        self.assertEqual(result, 'Hello ! Data more data  test')
        self.assertEqual(self.processor.matches, ['World', 'Testing...'])

    def test_process_chunk_json(self):
        result = self.json_processor.process_chunk('Data ```json\n\n{"key": "value"}\n\n``` more data')
        self.assertEqual(result, 'Data  more data')
        self.assertEqual(self.json_processor.matches, ['{"key": "value"}'])
    
    def test_process_chunk_json_extra_data(self):
        result = self.json_processor.process_chunk('Data```test```\n```json\n\n{"key": "value"}\n\n```')
        self.assertEqual(result, 'Data```test```\n')
        self.assertEqual(self.json_processor.matches, ['{"key": "value"}'])

    def test_process_chunk_json_with_tags(self):
        result = self.json_processor.process_chunk('Data```test```\n```json\n\n{"key": "value"}\n\n``` more data <think>Testing...</think>')
        self.assertEqual(result, 'Data```test```\n more data <think>Testing...</think>')
        self.assertEqual(self.json_processor.matches, ['{"key": "value"}'])

    def test_real_world_example(self):
        result = self.tool_processor.process_chunk('```tool_code\n{"action": "FilesAction.run_python_script", "arguments": {"file_path": "UsefulScripts/news_downloader.py"}}\n```')
        self.assertEqual(result, '')
        self.assertEqual(self.tool_processor.matches, ['{"action": "FilesAction.run_python_script", "arguments": {"file_path": "UsefulScripts/news_downloader.py"}}'])

if __name__ == '__main__':
    unittest.main() 