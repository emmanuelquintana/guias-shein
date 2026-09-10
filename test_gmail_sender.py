import unittest
from datetime import datetime
from unittest.mock import patch

from gmail_sender import _email_marketplace, _marketplace, describe_days, send_marketplace_emails


class GmailSenderTest(unittest.TestCase):
    def test_recognizes_marketplaces_and_formats_multiple_days(self):
        self.assertEqual(_marketplace("Marcas Guias shein 07-09-2026.pdf"), "Shein")
        self.assertEqual(_marketplace("TikTok Guias tiktok 07-09-2026.pdf"), "TikTok")
        self.assertEqual(_marketplace("ML_guias_07-09-2026.pdf"), "Mercado Libre")
        self.assertEqual(_marketplace("Amazon_Facturas_07-09-2026.pdf"), "Amazon")
        self.assertIsNone(_email_marketplace("ML_guias_07-09-2026.pdf"))
        self.assertIsNone(_email_marketplace("TikTok Guias tiktok - tiktok laser.pdf"))
        self.assertEqual(
            _email_marketplace("TikTok Guias tiktok - laser (solo impares).pdf"),
            "TikTok",
        )
        self.assertEqual(
            describe_days(["Pedidos Viernes.pdf", "Pedidos Sabado.pdf", "Pedidos Domingo.pdf"]),
            "Viernes, Sábado y Domingo",
        )

    def test_uses_current_day_when_filename_has_no_day(self):
        self.assertEqual(
            describe_days(["Amazon_Facturas_07-09-2026.pdf"], datetime(2026, 9, 7)),
            "Lunes",
        )

    def test_sends_each_day_as_a_separate_message(self):
        class FakePath:
            def __init__(self, name):
                self.name = name

            def read_bytes(self):
                return b"%PDF-test"

        class FakeSmtp:
            sent = []

            def __init__(self, *args, **kwargs):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

            def login(self, sender, password):
                pass

            def sendmail(self, sender, recipients, message):
                self.sent.append((tuple(recipients), message))

        batches = {
            ("Shein", "Viernes"): [FakePath("shein-viernes.pdf")],
            ("Shein", "Sábado"): [FakePath("shein-sabado.pdf")],
        }
        with patch("gmail_sender.group_email_batches", return_value=batches), patch(
            "gmail_sender.smtplib.SMTP_SSL", FakeSmtp
        ):
            result = send_marketplace_emails(
                "origen@gmail.com",
                "secret",
                ("destino1@gmail.com", "destino2@gmail.com"),
                ".",
            )

        self.assertEqual(len(FakeSmtp.sent), 2)
        self.assertTrue(
            all(recipients == ("destino1@gmail.com", "destino2@gmail.com") for recipients, _ in FakeSmtp.sent)
        )
        self.assertEqual(set(result), {"Shein - Viernes", "Shein - Sábado"})


if __name__ == "__main__":
    unittest.main()
