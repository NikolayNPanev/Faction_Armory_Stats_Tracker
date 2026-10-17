import unittest

from app_paths import get_app_data_dir


class AppPathsTest(unittest.TestCase):
    def test_development_data_dir_exists(self):
        self.assertTrue(get_app_data_dir().is_dir())


if __name__ == "__main__":
    unittest.main()