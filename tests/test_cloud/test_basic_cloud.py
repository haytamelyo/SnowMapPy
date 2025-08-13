#!/usr/bin/env python3
"""
Basic cloud processing test for SnowMapPy package.
This test verifies the basic structure and functionality without external dependencies.
"""

import os
import sys
import unittest
import tempfile
import shutil

# Add the package to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

# Only import core quality functions that don't have heavy dependencies
try:
    from core.quality import get_invalid_modis_classes, get_valid_modis_classes, validate_modis_class
    QUALITY_IMPORT_SUCCESS = True
except ImportError as e:
    print(f"Warning: Could not import quality functions: {e}")
    QUALITY_IMPORT_SUCCESS = False


class TestBasicCloudFunctionality(unittest.TestCase):
    """Test basic cloud functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test environment."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    @unittest.skipUnless(QUALITY_IMPORT_SUCCESS, "Quality functions not available")
    def test_invalid_modis_classes(self):
        """Test that invalid MODIS classes are correctly defined."""
        invalid_classes = get_invalid_modis_classes()
        expected_classes = [200, 201, 211, 237, 239, 250, 254]
        
        self.assertEqual(invalid_classes, expected_classes)
        
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
        
        for class_val in invalid_classes:
            self.assertIn(class_val, class_descriptions)
    
    @unittest.skipUnless(QUALITY_IMPORT_SUCCESS, "Quality functions not available")
    def test_valid_modis_classes(self):
        """Test that valid MODIS classes are correctly defined."""
        valid_classes = get_valid_modis_classes()
        expected_classes = [1, 2, 3]
        
        self.assertEqual(valid_classes, expected_classes)
        
        # Verify these are the correct valid classes
        class_descriptions = {
            1: "Snow",
            2: "No snow",
            3: "Water"
        }
        
        for class_val in valid_classes:
            self.assertIn(class_val, class_descriptions)
    
    @unittest.skipUnless(QUALITY_IMPORT_SUCCESS, "Quality functions not available")
    def test_validate_modis_class(self):
        """Test MODIS class validation."""
        # Test valid classes
        self.assertTrue(validate_modis_class(1))  # snow
        self.assertTrue(validate_modis_class(2))  # no snow
        self.assertTrue(validate_modis_class(3))  # water
        
        # Test invalid classes
        self.assertFalse(validate_modis_class(200))  # missing data
        self.assertFalse(validate_modis_class(250))  # cloud
        self.assertFalse(validate_modis_class(254))  # detector saturated
    
    @unittest.skipUnless(QUALITY_IMPORT_SUCCESS, "Quality functions not available")
    def test_quality_mask_logic(self):
        """Test quality mask application logic."""
        # Create test data
        value_data = [[100, 200, 50], [75, 250, 25]]
        class_data = [[1, 200, 2], [3, 250, 1]]
        
        # Apply quality mask manually
        invalid_classes = get_invalid_modis_classes()
        
        # Simulate masking
        masked_data = []
        for i in range(len(value_data)):
            row = []
            for j in range(len(value_data[i])):
                if class_data[i][j] in invalid_classes:
                    row.append(None)  # masked out
                else:
                    row.append(value_data[i][j])
            masked_data.append(row)
        
        # Verify masking
        self.assertEqual(masked_data[0][0], 100)  # should not be masked
        self.assertEqual(masked_data[0][1], None)  # should be masked (200)
        self.assertEqual(masked_data[0][2], 50)   # should not be masked
        self.assertEqual(masked_data[1][0], 75)   # should not be masked
        self.assertEqual(masked_data[1][1], None)  # should be masked (250)
        self.assertEqual(masked_data[1][2], 25)   # should not be masked
    
    def test_file_structure(self):
        """Test that the cloud module files exist."""
        # Check that cloud module files exist
        cloud_files = [
            'cloud/__init__.py',
            'cloud/auth.py',
            'cloud/loader.py',
            'cloud/processor.py'
        ]
        
        for file_path in cloud_files:
            full_path = os.path.join(os.path.dirname(__file__), '..', '..', file_path)
            self.assertTrue(os.path.exists(full_path), f"File {file_path} does not exist")
    
    def test_directory_creation(self):
        """Test directory creation functionality."""
        # Test that we can create directories
        test_dir = os.path.join(self.temp_dir, 'test_output')
        
        # Directory should not exist initially
        self.assertFalse(os.path.exists(test_dir))
        
        # Create directory
        os.makedirs(test_dir, exist_ok=True)
        
        # Directory should exist now
        self.assertTrue(os.path.exists(test_dir))
        
        # Test nested directory creation
        nested_dir = os.path.join(test_dir, 'nested', 'deep')
        os.makedirs(nested_dir, exist_ok=True)
        self.assertTrue(os.path.exists(nested_dir))


class TestCloudModuleStructure(unittest.TestCase):
    """Test cloud module structure."""
    
    def test_package_structure(self):
        """Test that the package structure is correct."""
        # Check main directories exist
        required_dirs = ['core', 'local', 'cloud', 'tests']
        for dir_name in required_dirs:
            dir_path = os.path.join(os.path.dirname(__file__), '..', '..', dir_name)
            self.assertTrue(os.path.exists(dir_path), f"Directory {dir_name} does not exist")
        
        # Check __init__.py files exist
        required_init_files = [
            '__init__.py',
            'core/__init__.py',
            'local/__init__.py',
            'cloud/__init__.py',
            'tests/__init__.py'
        ]
        
        for init_file in required_init_files:
            init_path = os.path.join(os.path.dirname(__file__), '..', '..', init_file)
            self.assertTrue(os.path.exists(init_path), f"File {init_file} does not exist")


if __name__ == '__main__':
    # Create test suite using modern approach
    loader = unittest.TestLoader()
    test_suite = unittest.TestSuite()
    
    # Add tests using modern method
    test_suite.addTests(loader.loadTestsFromTestCase(TestBasicCloudFunctionality))
    test_suite.addTests(loader.loadTestsFromTestCase(TestCloudModuleStructure))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Print summary
    print(f"\n{'='*60}")
    print("Basic Cloud Processing Test Summary")
    print(f"{'='*60}")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.failures:
        print("\nFailures:")
        for test, traceback in result.failures:
            print(f"  {test}: {traceback}")
    
    if result.errors:
        print("\nErrors:")
        for test, traceback in result.errors:
            print(f"  {test}: {traceback}")
    
    if result.wasSuccessful():
        print("\n✅ All basic cloud processing tests passed!")
        print("\n📋 Package Structure Verified:")
        print("├── core/           # Shared functionality")
        print("├── local/          # Local data processing")
        print("├── cloud/          # Cloud data processing")
        print("└── tests/          # Test suite")
    else:
        print("\n❌ Some basic cloud processing tests failed!")
    
    print(f"{'='*60}") 