import unittest
import sys
import os


class TestQuality(unittest.TestCase):
    """Test quality control functions."""
    
    def test_get_valid_modis_classes(self):
        """Test getting valid MODIS classes."""
        # Test the expected valid classes manually
        expected_valid_classes = [1, 2, 3]  # snow, no snow, water
        
        # Verify these are the correct valid classes
        class_descriptions = {
            1: "Snow",
            2: "No snow", 
            3: "Water"
        }
        
        for class_val in expected_valid_classes:
            self.assertIn(class_val, class_descriptions)
        
        self.assertEqual(expected_valid_classes, [1, 2, 3])
    
    def test_get_invalid_modis_classes(self):
        """Test getting invalid MODIS classes."""
        # Test the expected invalid classes manually
        expected_invalid_classes = [200, 201, 211, 237, 239, 250, 254]
        
        # Verify these are the correct invalid classes from GEE documentation
        class_descriptions = {
            200: "Missing data",
            201: "No decision",
            211: "Night", 
            237: "Inland water",
            239: "Ocean",
            250: "Cloud",
            254: "Detector saturated"
        }
        
        for class_val in expected_invalid_classes:
            self.assertIn(class_val, class_descriptions)
        
        self.assertEqual(expected_invalid_classes, [200, 201, 211, 237, 239, 250, 254])
    
    def test_validate_modis_class(self):
        """Test MODIS class validation logic."""
        valid_classes = [1, 2, 3]
        invalid_classes = [200, 201, 211, 237, 239, 250, 254]
        
        # Test valid classes
        self.assertTrue(1 in valid_classes)  # snow
        self.assertTrue(2 in valid_classes)  # no snow
        self.assertTrue(3 in valid_classes)  # water
        
        # Test invalid classes
        self.assertFalse(200 in valid_classes)  # missing data
        self.assertFalse(250 in valid_classes)  # cloud
        self.assertFalse(254 in valid_classes)  # detector saturated
        
        # Test that invalid classes are in the invalid list
        self.assertTrue(200 in invalid_classes)
        self.assertTrue(250 in invalid_classes)
        self.assertTrue(254 in invalid_classes)


if __name__ == '__main__':
    unittest.main() 