import unittest
import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from src.scraper import filtrar_titulares

class TestScraper(unittest.TestCase):

    def test_filtrar_titulares(self):
        """Test the filtrar_titulares function."""
        # Arrange
        titulares = [
            ("Este es un titular de más de 20 caracteres", "http://example.com/1"),
            ("Este es otro titular de más de 20 caracteres", "http://example.com/2"),
            ("Corto", "http://example.com/3"),
            ("Este es un titular de más de 20 caracteres", "http://example.com/4"), # Duplicate
        ]

        # Act
        titulares_filtrados = filtrar_titulares(titulares)

        # Assert
        self.assertEqual(len(titulares_filtrados), 2)
        self.assertEqual(titulares_filtrados[0][0], "Este es un titular de más de 20 caracteres")
        self.assertEqual(titulares_filtrados[1][0], "Este es otro titular de más de 20 caracteres")

if __name__ == '__main__':
    unittest.main()
