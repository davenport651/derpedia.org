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

    @patch('app.client')
    def test_title_extraction_success(self, mock_client):
        # Mock the response from generate_content
        mock_response = MagicMock()
        mock_response.text = "# The Correct Title\n\n| Key | Value |\n|---|---|\n"

        mock_client.models.generate_content.return_value = mock_response

        # Mock image generation to avoid failure or 404
        mock_client.models.generate_images.return_value = MagicMock(generated_images=[])

        # Monkeypatch API_KEY
        app_module.API_KEY = "test_key"
        app_module.client = mock_client

        response = self.app.post('/search', data={'q': 'Test Query'})

        self.assertEqual(response.status_code, 200)
        # Check if title extraction worked
        self.assertIn(b"The Correct Title", response.data)

    @patch('app.client')
    def test_title_extraction_fallback(self, mock_client):
        mock_response = MagicMock()
        # No # Title at start
        mock_response.text = "| Key | Value |\n|---|---|\n"

        mock_client.models.generate_content.return_value = mock_response
        mock_client.models.generate_images.return_value = MagicMock(generated_images=[])

        app_module.API_KEY = "test_key"
        app_module.client = mock_client

        response = self.app.post('/search', data={'q': 'My Query'})

        self.assertEqual(response.status_code, 200)
        # Should fallback to query
        self.assertIn(b"My Query", response.data)

    @patch('app.client')
    def test_query_none_fallback(self, mock_client):
        # Test the "The Void" fallback when q is empty
        mock_response = MagicMock()
        mock_response.text = "# The Void\nContent"
        mock_client.models.generate_content.return_value = mock_response
        mock_client.models.generate_images.return_value = MagicMock(generated_images=[])

        app_module.API_KEY = "test_key"
        app_module.client = mock_client

        # Send empty q
        response = self.app.post('/search', data={'q': ''})

        # We expect the PROMPT to have used "The Void"
        call_args = mock_client.models.generate_content.call_args
        kwargs = call_args.kwargs if call_args.kwargs else {}
        contents = kwargs.get('contents', '')

        self.assertIn("The Void", contents)

if __name__ == '__main__':
    unittest.main()
