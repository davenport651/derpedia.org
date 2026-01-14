import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Ensure app is importable
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import app
import app as app_module

class DerpediaTests(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    @patch('app.check_reality', return_value=True)
    @patch('app.client')
    def test_title_extraction_success(self, mock_client, mock_check_reality):
        # Mock object that handles both text and image calls
        mock_response = MagicMock()
        mock_response.text = "# The Correct Title\n\n| Key | Value |\n|---|---|\n"
        mock_response.candidates = [] # No image candidates

        mock_client.models.generate_content.return_value = mock_response

        # Monkeypatch API_KEY
        app_module.API_KEY = "test_key"
        app_module.client = mock_client

        response = self.app.post('/search', data={'q': 'Test Query'})

        self.assertEqual(response.status_code, 200)
        # Check if title extraction worked
        self.assertIn(b"The Correct Title", response.data)

    @patch('app.check_reality', return_value=True)
    @patch('app.client')
    def test_title_extraction_fallback(self, mock_client, mock_check_reality):
        mock_response = MagicMock()
        mock_response.text = "| Key | Value |\n|---|---|\n"
        mock_response.candidates = []

        mock_client.models.generate_content.return_value = mock_response

        app_module.API_KEY = "test_key"
        app_module.client = mock_client

        response = self.app.post('/search', data={'q': 'My Query'})

        self.assertEqual(response.status_code, 200)
        # Should fallback to query
        self.assertIn(b"My Query", response.data)

    @patch('app.check_reality', return_value=True)
    @patch('app.client')
    def test_query_none_fallback(self, mock_client, mock_check_reality):
        # Test the "The Void" fallback when q is empty
        mock_response = MagicMock()
        mock_response.text = "# The Void\nContent"
        mock_response.candidates = []

        mock_client.models.generate_content.return_value = mock_response

        app_module.API_KEY = "test_key"
        app_module.client = mock_client

        # Send empty q
        response = self.app.post('/search', data={'q': ''})

        # We expect the FIRST call to generate_content to have "The Void"
        # Since generate_content is called twice (text then image), check call_args_list
        # call_args_list[0] is text gen, call_args_list[1] is image gen

        self.assertTrue(mock_client.models.generate_content.called)
        first_call_args = mock_client.models.generate_content.call_args_list[0]

        kwargs = first_call_args.kwargs if first_call_args.kwargs else {}
        # contents might be in kwargs or args[1] depending on how it's called
        # app.py uses keyword argument 'contents'
        contents = kwargs.get('contents', '')

        self.assertIn("The Void", contents)

if __name__ == '__main__':
    unittest.main()
