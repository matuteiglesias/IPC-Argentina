import unittest

from arg_price.normalize import cordoba_csv, neuquen_calculator_json


class CordobaLiveShapeTests(unittest.TestCase):
    def meta(self):
        return {
            "source_id": "cordoba_ipc",
            "sha256": "fixture-sha",
            "parser_id": "cordoba_ipc/empalmed-semicolon-cp1252-v2",
        }

    def test_cp1252_semicolon_preamble_and_decimal_comma(self):
        text = "\n".join(
            [
                "Índice de Precios al Consumidor de Córdoba. Nivel General y principales aperturas. Base Jun-Nov 2025 = 100;;;;",
                "Índice mensual empalmado con la serie anterior (base 2014 = 100).;;;;",
                "Enero 2014 - Noviembre 2025 (1);;;;",
                ";;;;",
                "COICOP;Descripción;oct-25;nov-25",
                ";NIVEL GENERAL;102,98;105,67",
                "A01;ALIMENTOS Y BEBIDAS NO ALCOHÓLICAS;102,20;105,91",
            ]
        ).encode("cp1252")
        rows = cordoba_csv(text, self.meta())
        self.assertEqual([r["period"] for r in rows], ["2025-10-01", "2025-11-01"])
        self.assertEqual([r["source_index"] for r in rows], [102.98, 105.67])
        self.assertTrue(all(r["parser_id"].endswith("cp1252-v2") for r in rows))
        self.assertTrue(all("encoding=cp1252" in r["source_base_or_vintage"] for r in rows))

    def test_header_discovery_fails_closed_when_ambiguous(self):
        text = "COICOP;Descripción;ene-25\n;NIVEL GENERAL;100\nCOICOP;Descripción;feb-25\n;NIVEL GENERAL;101\n"
        with self.assertRaisesRegex(ValueError, "cordoba_header_count:2"):
            cordoba_csv(text.encode("utf-8"), self.meta())


class NeuquenLiveShapeTests(unittest.TestCase):
    def meta(self):
        return {
            "source_id": "neuquen_ipc_provincial",
            "sha256": "fixture-sha",
            "parser_id": "neuquen_ipc_provincial/calculator-json-v1",
        }

    def test_calculator_payload_maps_observed_levels_exactly(self):
        raw = b'[{"anio":"2026","mes":"5","indice":"1549.30"},{"anio":"2026","mes":"6","indice":"1583.00"},{"anio":"2026","mes":"7","indice":"1619.70"}]'
        rows = neuquen_calculator_json(raw, self.meta())
        self.assertEqual([r["period"] for r in rows], ["2026-05-01", "2026-06-01", "2026-07-01"])
        self.assertEqual([r["source_index"] for r in rows], [1549.30, 1583.00, 1619.70])
        self.assertTrue(all(r["value_status"] == "observed" for r in rows))
        self.assertTrue(all("2022=100" in r["source_base_or_vintage"] for r in rows))

    def test_calculator_payload_fails_closed_on_schema_drift(self):
        raw = b'[{"anio":"2026","mes":"7","indice":"1619.70","variacion":"2.3"}]'
        with self.assertRaisesRegex(ValueError, "neuquen_schema_row:0"):
            neuquen_calculator_json(raw, self.meta())


if __name__ == "__main__":
    unittest.main()
