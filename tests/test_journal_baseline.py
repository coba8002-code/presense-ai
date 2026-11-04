import unittest
import test_journal_summary as fixtures
class BaselineTests(unittest.TestCase):
 setUp=fixtures.SummaryTests.setUp
 case=fixtures.SummaryTests.case
 def test_record_pattern_not_model_frequency(self):
  for day in range(1,6):self.case(day*86400)
  self.case(0)
  r=self.store.summary(self.token,self.pet,30)['record_pattern']
  self.assertTrue(r['ready']);self.assertEqual(r['historical_days'],5);self.assertEqual(r['median_records_per_recorded_day'],1.)
  self.assertEqual(r['current_day_records'],1);self.assertIsNone(r['model_revision']);self.assertFalse(r['measured_behavior_baseline'])
 def test_insufficient_no_record_does_not_mean_zero_behavior(self):
  self.case(86400)
  r=self.store.summary(self.token,self.pet,30)['record_pattern']
  self.assertFalse(r['ready']);self.assertIsNone(r['current_day_records']);self.assertIsNone(r['median_records_per_recorded_day'])
