import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from analysis import NewsAnalyzer

class TestNewsAnalyzer(unittest.TestCase):

    @patch('analysis.pipeline')
    @patch('analysis.spacy.load')
    def test_initialization(self, mock_spacy_load, mock_pipeline):
        """Test that the NewsAnalyzer class can be instantiated and models are loaded."""
        # Arrange
        mock_pipeline.return_value = MagicMock()
        mock_spacy_load.return_value = MagicMock()

        # Act
        analyzer = NewsAnalyzer()

        # Assert
        self.assertIsNotNone(analyzer.sentiment_analyzer)
        self.assertIsNotNone(analyzer.entity_extractor)
        self.assertIsNotNone(analyzer.summarizer)
        self.assertIsNotNone(analyzer.zero_shot_classifier)
        self.assertEqual(mock_pipeline.call_count, 3)
        mock_spacy_load.assert_called_once()

if __name__ == '__main__':
    unittest.main()
