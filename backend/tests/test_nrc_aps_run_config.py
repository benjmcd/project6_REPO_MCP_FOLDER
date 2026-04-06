import unittest

from app.services import connectors_nrc_adams


class TestNrcApsRunConfig(unittest.TestCase):
    def test_normalize_request_config_preserves_processing_overrides(self):
        config = connectors_nrc_adams._normalize_request_config(
            {
                "mode": "strict_builder",
                "wire_shape_mode": "shape_a",
                "content_sniff_bytes": 8192,
                "content_parse_max_pages": 750,
                "content_parse_timeout_seconds": 0,
                "ocr_enabled": False,
                "ocr_max_pages": 7,
                "ocr_render_dpi": 200,
                "ocr_language": "eng",
                "ocr_timeout_seconds": 45,
                "content_min_searchable_chars": 10,
                "content_min_searchable_tokens": 2,
            },
            "local-proof",
        )

        self.assertEqual(config["content_sniff_bytes"], 8192)
        self.assertEqual(config["content_parse_max_pages"], 750)
        self.assertEqual(config["content_parse_timeout_seconds"], 0)
        self.assertFalse(config["ocr_enabled"])
        self.assertEqual(config["ocr_max_pages"], 7)
        self.assertEqual(config["ocr_render_dpi"], 200)
        self.assertEqual(config["ocr_language"], "eng")
        self.assertEqual(config["ocr_timeout_seconds"], 45)
        self.assertEqual(config["content_min_searchable_chars"], 10)
        self.assertEqual(config["content_min_searchable_tokens"], 2)

    def test_lenient_pass_through_excludes_processing_controls_from_query_payload(self):
        config = connectors_nrc_adams._normalize_request_config(
            {
                "mode": "lenient_pass_through",
                "wire_shape_mode": "shape_a",
                "q": "inspection",
                "content_parse_timeout_seconds": 0,
                "ocr_enabled": False,
            },
            "local-proof",
        )

        self.assertEqual(config["query_payload_inbound"]["q"], "inspection")
        self.assertNotIn("content_parse_timeout_seconds", config["query_payload_inbound"])
        self.assertNotIn("ocr_enabled", config["query_payload_inbound"])
        self.assertEqual(config["content_parse_timeout_seconds"], 0)
        self.assertFalse(config["ocr_enabled"])

    def test_visual_lane_mode_defaults_to_baseline(self):
        """Absent visual_lane_mode must default to baseline (fail-closed)."""
        config = connectors_nrc_adams._normalize_request_config(
            {
                "mode": "strict_builder",
                "wire_shape_mode": "shape_a",
            },
            "local-proof",
        )

        self.assertEqual(config["visual_lane_mode"], "baseline")

    def test_visual_lane_mode_preserves_baseline(self):
        """Explicit baseline value must be preserved."""
        config = connectors_nrc_adams._normalize_request_config(
            {
                "mode": "strict_builder",
                "wire_shape_mode": "shape_a",
                "visual_lane_mode": "baseline",
            },
            "local-proof",
        )

        self.assertEqual(config["visual_lane_mode"], "baseline")

    def test_visual_lane_mode_fail_closed_for_invalid_value(self):
        """Invalid visual_lane_mode must fail closed to baseline."""
        config = connectors_nrc_adams._normalize_request_config(
            {
                "mode": "strict_builder",
                "wire_shape_mode": "shape_a",
                "visual_lane_mode": "invalid_mode",
            },
            "local-proof",
        )

        self.assertEqual(config["visual_lane_mode"], "baseline")

    def test_visual_lane_mode_fail_closed_for_unsupported_variant(self):
        """Non-baseline values must fail closed to baseline in baseline-only phase."""
        config = connectors_nrc_adams._normalize_request_config(
            {
                "mode": "strict_builder",
                "wire_shape_mode": "shape_a",
                "visual_lane_mode": "experimental_a",
            },
            "local-proof",
        )

        self.assertEqual(config["visual_lane_mode"], "baseline")

    def test_visual_lane_mode_excluded_from_query_payload(self):
        """visual_lane_mode must not leak into query_payload_inbound."""
        config = connectors_nrc_adams._normalize_request_config(
            {
                "mode": "lenient_pass_through",
                "wire_shape_mode": "shape_a",
                "q": "inspection",
                "visual_lane_mode": "baseline",
            },
            "local-proof",
        )

        self.assertEqual(config["visual_lane_mode"], "baseline")
        self.assertNotIn("visual_lane_mode", config["query_payload_inbound"])
