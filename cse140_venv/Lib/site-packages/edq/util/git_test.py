import os

import edq.testing.unittest
import edq.util.dirent
import edq.util.git

THIS_DIR = os.path.abspath(os.path.dirname(os.path.realpath(__file__)))

class TestGit(edq.testing.unittest.BaseTest):
    """ Test git functionality. """

    def test_version_in_repo(self) -> None:
        """ Test getting a git version inside of a repo. """

        version = edq.util.git.get_version(THIS_DIR)
        self.assertNotEqual(edq.util.git.UNKNOWN_VERSION, version, 'Got an unknown version (assumes test is run in a repo).')

    def test_version_cwd(self) -> None:
        """ Test getting a git version using the current working directory. """

        version = edq.util.git.get_version()
        self.assertNotEqual(edq.util.git.UNKNOWN_VERSION, version, 'Got an unknown version (assumes test is run in a repo)')

    def test_version_not_in_repo(self) -> None:
        """ Test getting a git version when not inside of a repo. """

        path = edq.util.dirent.get_temp_path(prefix = 'edq-test-git-')
        version = edq.util.git.get_version(path)
        self.assertEqual(edq.util.git.UNKNOWN_VERSION, version)
