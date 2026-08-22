from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from lavesecexpress_etl.sources.bank3.parser import parse_bank3


HEADER = (
    "Data Lançamento,Data Contábil,Título,Descrição,"
    "Entrada(R$),Saída(R$),Saldo do Dia(R$)"
)


def _write_csv(tmp_path: Path, transaction_line: str) -> Path:
    file_path = tmp_path / "bank3.csv"
    file_path.write_text(
        f"EXTRATO DE CONTA CORRENTE C6 BANK\n\n{HEADER}\n{transaction_line}\n",
        encoding="utf-8",
    )
    return file_path


class TestBank3Parser(unittest.TestCase):
    def _parse(self, transaction_line: str):
        with TemporaryDirectory() as tmp_dir:
            file_path = _write_csv(Path(tmp_dir), transaction_line)
            return parse_bank3(str(file_path))

    def test_preserves_regular_rows(self):
        result = self._parse(
            '21/08/2026,21/08/2026,"Pix enviado",PAGTO PIX,'
            "0.00,1090.85,580.60"
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result.iloc[0]["titulo"], "Pix enviado")
        self.assertAlmostEqual(result.iloc[0]["saida"], 1090.85)

    def test_recovers_fully_quoted_rows(self):
        result = self._parse(
            '"21/08/2026,21/08/2026,""Pix enviado"",PAGTO PIX,'
            '0.00,1090.85,580.60"'
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result.iloc[0]["titulo"], "Pix enviado")
        self.assertAlmostEqual(result.iloc[0]["saida"], 1090.85)

    def test_rejects_unrecoverable_transaction_rows(self):
        with self.assertRaisesRegex(
            ValueError,
            r"Linha 4 inválida.*esperadas 7.*encontradas 4",
        ):
            self._parse("21/08/2026,21/08/2026,linha,incompleta")


if __name__ == "__main__":
    unittest.main()
