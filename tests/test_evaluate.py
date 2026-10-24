import unittest

from eval.evaluate import calculate_metrics


class CalculateMetricsTests(unittest.TestCase):
    def test_first_rank_matches(self):
        self.assertEqual(
            calculate_metrics(["a", "b"], [["a"], ["b", "c"]]),
            {"recall": 1.0, "mrr": 1.0},
        )

    def test_each_rank_in_top_three(self):
        for rank in (1, 2, 3):
            with self.subTest(rank=rank):
                metrics = calculate_metrics(["target"], [["other"] * (rank - 1) + ["target"]])
                self.assertEqual(metrics["recall"], 1.0)
                self.assertAlmostEqual(metrics["mrr"], 1 / rank)

    def test_missing_and_empty_results(self):
        self.assertEqual(
            calculate_metrics(["a", "b"], [["other"], []]),
            {"recall": 0.0, "mrr": 0.0},
        )

    def test_fourth_rank_is_excluded(self):
        self.assertEqual(
            calculate_metrics(["target"], [["a", "b", "c", "target"]]),
            {"recall": 0.0, "mrr": 0.0},
        )

    def test_duplicate_documents_use_first_match(self):
        metrics = calculate_metrics(["target"], [["other", "target", "target"]])
        self.assertEqual(metrics, {"recall": 1.0, "mrr": 0.5})

    def test_mixed_matches_include_misses_in_average(self):
        metrics = calculate_metrics(
            ["a", "b", "c", "d"],
            [["a"], ["x", "b"], ["x", "y", "c"], []],
        )
        self.assertEqual(metrics["recall"], 0.75)
        self.assertAlmostEqual(metrics["mrr"], (1 + 1 / 2 + 1 / 3) / 4)

    def test_reported_fifteen_question_result(self):
        metrics = calculate_metrics(
            ["target"] * 15,
            [["target"] for _ in range(12)]
            + [["other", "target"], ["other", "target"], ["a", "b", "target"]],
        )
        self.assertEqual(metrics["recall"], 1.0)
        self.assertAlmostEqual(metrics["mrr"], 8 / 9)

    def test_empty_expected_raises(self):
        with self.assertRaisesRegex(ValueError, "Expected list cannot be empty"):
            calculate_metrics([], [])

    def test_mismatched_lengths_raise(self):
        for expected, retrieved in ((["a"], []), (["a"], [["a"], ["b"]])):
            with self.subTest(expected=expected, retrieved=retrieved):
                with self.assertRaisesRegex(ValueError, "same length"):
                    calculate_metrics(expected, retrieved)


if __name__ == "__main__":
    unittest.main()
