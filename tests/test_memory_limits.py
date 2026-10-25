import unittest
from deploy.enable_memory_limits import updated
class MemoryTests(unittest.TestCase):
 def test_preserves_boot_settings_and_is_idempotent(self):
  original='console=tty1 root=PARTUUID=test rootwait cfg80211.ieee80211_regdom=US\n'
  result=updated(original);self.assertTrue(result.startswith(original.strip()));self.assertEqual(result.count('cgroup_enable=memory'),1);self.assertEqual(updated(result),result)
 def test_refuses_multiline(self):
  with self.assertRaises(ValueError):updated('first\nsecond\n')
