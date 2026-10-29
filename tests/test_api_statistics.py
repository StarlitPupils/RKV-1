import json,sys,unittest
from pathlib import Path
from scripts.api_statistics import wilson,cost_band
class Costs(unittest.TestCase):
 def test_intervals_include_fixed_proportion_and_keep_small_sample_uncertainty(self):
  for n in (12,16):
   for k in range(n+1):
    v=wilson(k,n);self.assertLessEqual(v['low'],k/n+1e-15);self.assertGreaterEqual(v['high']+1e-15,k/n)
  with self.assertRaises(ValueError):wilson(0,0)
 def test_cache_usage_conservation_and_unknown_not_zero(self):
  b=json.loads(Path('docs/api-reference-price-book.json').read_bytes());u={'prompt_cache_hit_tokens':1000000,'prompt_cache_miss_tokens':1000000,'prompt_tokens':2000000,'completion_tokens':1000000};x=cost_band(u,b);self.assertAlmostEqual(x['low'],.753);self.assertAlmostEqual(x['high'],1.506);self.assertIsNone(cost_band(None,b));self.assertIsNone(cost_band({'completion_tokens':4},b));self.assertIsNone(cost_band({**u,'prompt_tokens':0},b))
if __name__=='__main__':unittest.main()
