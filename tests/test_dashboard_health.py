import unittest
from unittest.mock import patch
from app.routers import status as router

class DashboardHealthTests(unittest.TestCase):
 def test_health_warnings_reach_dashboard_without_an_extra_system_probe(self):
  for state,expected in [('warning','degraded'),('error','error'),('ok','ok')]:
   data={'status':{'state':'ok','issues':[]}}
   health={'state':state,'problems':[] if state=='ok' else [{'message':'Browser reviews due'}],'source_checks':{'browser_review':{'overdue':2}}}
   with patch.object(router,'get_status',return_value=data) as probe,patch('app.services.integration_health.collect',return_value=health) as collect:
    result=router.status()
   probe.assert_called_once();collect.assert_called_once_with(data)
   self.assertEqual(result['status']['state'],expected)
   self.assertEqual(result['status']['health']['source_checks']['browser_review']['overdue'],2)
   self.assertEqual(bool(result['status']['issues']),state!='ok')

if __name__=='__main__':unittest.main()
