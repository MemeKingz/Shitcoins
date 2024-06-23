import unittest

from shitcoins.get_holders import _filter_duplicate_keys_from_list_of_dict
from shitcoins.model.holder import Holder


class TestGetHolders(unittest.TestCase):

    def test_filter_duplicate_keys_from_list_of_dict_two_same_addresses(self):
        holder_addresses = [Holder(address='123'), Holder(address='234'), Holder(address='123')]
        holder_addresses = _filter_duplicate_keys_from_list_of_dict(holder_addresses)
        self.assertEqual(2, len(holder_addresses))

    def test_filter_duplicate_keys_from_list_of_dict_empty_does_not_fail(self):
        holder_addresses = _filter_duplicate_keys_from_list_of_dict([])
        self.assertEqual(0, len(holder_addresses))
