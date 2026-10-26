"""Analytic cross-checks of information accounting, without scientific inputs."""
import math
import unittest

from scripts.audit_cdf_information import information, controls


class InformationAccountingTests(unittest.TestCase):
    def test_known_probabilities_and_context(self):
        cdf = [0, 8192]
        for i in range(255):
            cdf.append(cdf[-1] + (24576 // 255) + (i < 24576 % 255))
        contexts = []
        def predict(context):
            contexts.append(list(context))
            return cdf
        bits, _ = information(bytes([0, 1, 0]), predict)
        self.assertAlmostEqual(bits, 4 - math.log2((cdf[2]-cdf[1])/32768), places=11)
        self.assertEqual(contexts, [[256]*4, [256,256,256,0], [256,256,0,1]])

    def test_invalid_cdf_rejected(self):
        for cdf in ((0, 32768), tuple([0]*256+[32768]), tuple(range(257))):
            with self.assertRaises(ValueError):
                information(b'a', lambda context: cdf)

    def test_synthetic_golden_and_exact_restore(self):
        rows = controls()
        self.assertEqual(len(rows), 3)
        for row in rows:
            self.assertTrue(row['exact'])
            self.assertTrue(row['engineering_gate_pass'])
            if row['uniform_golden_pass'] is not None:
                self.assertTrue(row['uniform_golden_pass'])


if __name__ == '__main__':
    unittest.main()
