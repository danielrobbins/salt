"""
    :codeauthor: Jayesh Kariya <jayeshk@saltstack.com>
"""

import os

import salt.states.blockdev as blockdev
import salt.utils.path
from tests.support.mixins import LoaderModuleMockMixin
from tests.support.mock import MagicMock, Mock, patch
from tests.support.unit import TestCase


class BlockdevTestCase(TestCase, LoaderModuleMockMixin):
    """
    Test cases for salt.states.blockdev
    """

    def setup_loader_modules(self):
        return {blockdev: {}}

    # 'tuned' function tests: 1

    def test_tuned(self):
        """
        Test to manage options of block device
        """
        name = "/dev/vg/master-data"

        ret = {"name": name, "result": True, "changes": {}, "comment": ""}

        comt = ("Changes to {} cannot be applied. " "Not a block device. ").format(name)
        with patch.dict(blockdev.__salt__, {"file.is_blkdev": False}):
            ret.update({"comment": comt})
            self.assertDictEqual(blockdev.tuned(name), ret)

        comt = "Changes to {} will be applied ".format(name)
        with patch.dict(blockdev.__salt__, {"file.is_blkdev": True}):
            ret.update({"comment": comt, "result": None})
            with patch.dict(blockdev.__opts__, {"test": True}):
                self.assertDictEqual(blockdev.tuned(name), ret)

    # 'formatted' function tests: 1

    def test_formatted(self):
        """
        Test to manage filesystems of partitions.
        """
        name = "/dev/vg/master-data"

        ret = {"name": name, "result": False, "changes": {}, "comment": ""}

        with patch.object(
            os.path, "exists", MagicMock(side_effect=[False, True, True, True, True])
        ):
            comt = "{} does not exist".format(name)
            ret.update({"comment": comt})
            self.assertDictEqual(blockdev.formatted(name), ret)

            mock_ext4 = MagicMock(return_value="ext4")

            # Test state return when block device is already in the correct state
            with patch.dict(blockdev.__salt__, {"cmd.run": mock_ext4}):
                comt = "{} already formatted with ext4".format(name)
                ret.update({"comment": comt, "result": True})
                self.assertDictEqual(blockdev.formatted(name), ret)

            # Test state return when provided block device is an invalid fs_type
            with patch.dict(blockdev.__salt__, {"cmd.run": MagicMock(return_value="")}):
                ret.update({"comment": "Invalid fs_type: foo-bar", "result": False})
                with patch.object(
                    salt.utils.path, "which", MagicMock(return_value=False)
                ):
                    self.assertDictEqual(
                        blockdev.formatted(name, fs_type="foo-bar"), ret
                    )

            # Test state return when provided block device state will change and test=True
            with patch.dict(
                blockdev.__salt__, {"cmd.run": MagicMock(return_value="new-thing")}
            ):
                comt = "Changes to {} will be applied ".format(name)
                ret.update({"comment": comt, "result": None})
                with patch.object(
                    salt.utils.path, "which", MagicMock(return_value=True)
                ):
                    with patch.dict(blockdev.__opts__, {"test": True}):
                        self.assertDictEqual(blockdev.formatted(name), ret)

            # Test state return when block device format fails
            with patch.dict(
                blockdev.__salt__,
                {
                    "cmd.run": MagicMock(return_value=mock_ext4),
                    "disk.format": MagicMock(return_value=True),
                },
            ):
                comt = "Failed to format {}".format(name)
                ret.update({"comment": comt, "result": False})
                with patch.object(
                    salt.utils.path, "which", MagicMock(return_value=True)
                ):
                    with patch.dict(blockdev.__opts__, {"test": False}):
                        self.assertDictEqual(blockdev.formatted(name), ret)

    def test__checkblk(self):
        """
        Confirm that we call cmd.run with ignore_retcode=True
        """
        cmd_mock = Mock()
        with patch.dict(blockdev.__salt__, {"cmd.run": cmd_mock}):
            blockdev._checkblk("/dev/foo")

        cmd_mock.assert_called_once_with(
            ["blkid", "-o", "value", "-s", "TYPE", "/dev/foo"], ignore_retcode=True
        )
