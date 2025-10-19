import unittest
from unittest.mock import patch
import pandas as pd
import sqlite3
import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from app import load_data

class TestApp(unittest.TestCase):

    def setUp(self):
        """Set up a temporary in-memory database for testing."""
        self.conn = sqlite3.connect(':memory:')
        self.conn.execute("""
            CREATE TABLE headlines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                headline TEXT NOT NULL,
                url TEXT NOT NULL,
                collection_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                sentiment_label TEXT,
                sentiment_score REAL,
                entities TEXT,
                topic TEXT
            )
        """)
        self.conn.execute("""
            INSERT INTO headlines (source, headline, url, sentiment_label, sentiment_score, entities, topic)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, ('Test-Source', 'Test Headline', 'http://example.com', 'NEU', 0.0, '[]', 'Test-Topic'))
        self.conn.commit()

    def tearDown(self):
        """Close the database connection."""
        self.conn.close()

    @patch('app.get_db_connection')
    def test_load_data(self, mock_get_db_connection):
        """Test the load_data function."""
        # Arrange
        mock_get_db_connection.return_value = self.conn

        # Act
        df = load_data()

        # Assert
        self.assertIsInstance(df, pd.DataFrame)
        self.assertEqual(len(df), 1)
        self.assertEqual(df.iloc[0]['headline'], 'Test Headline')

if __name__ == '__main__':
    unittest.main()
