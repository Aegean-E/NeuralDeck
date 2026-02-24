import unittest
import sys
import os
from unittest.mock import MagicMock, patch, mock_open

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from document_processor import (
    extract_text_from_document,
    check_llm_server,
    _extract_text_from_docx,
    _extract_text_from_pptx,
    _extract_text_from_txt
)


class TestExtractTextFromDocument(unittest.TestCase):
    @patch('document_processor._extract_text_from_docx')
    def test_extract_docx(self, mock_docx):
        mock_docx.return_value = "Docx content"
        result = extract_text_from_document("test.docx")
        self.assertEqual(result, "Docx content")
        mock_docx.assert_called_once_with("test.docx")

    @patch('document_processor._extract_text_from_pptx')
    def test_extract_pptx(self, mock_pptx):
        mock_pptx.return_value = "Pptx content"
        result = extract_text_from_document("test.pptx")
        self.assertEqual(result, "Pptx content")
        mock_pptx.assert_called_once_with("test.pptx")

    @patch('document_processor._extract_text_from_txt')
    def test_extract_txt(self, mock_txt):
        mock_txt.return_value = "Txt content"
        result = extract_text_from_document("test.txt")
        self.assertEqual(result, "Txt content")
        mock_txt.assert_called_once_with("test.txt")

    @patch('document_processor.extract_text_from_pdf')
    def test_extract_pdf(self, mock_pdf):
        mock_pdf.return_value = "Pdf content"
        result = extract_text_from_document("test.pdf")
        self.assertEqual(result, "Pdf content")
        mock_pdf.assert_called_once_with("test.pdf", None)

    def test_unsupported_format(self):
        with self.assertRaises(ValueError) as cm:
            extract_text_from_document("test.xyz")
        self.assertIn("Unsupported file type", str(cm.exception))


class TestExtractTextFromDocx(unittest.TestCase):
    @patch('document_processor.docx.Document')
    def test_docx_success(self, mock_document):
        mock_para = MagicMock()
        mock_para.text = "Paragraph 1"
        mock_doc = MagicMock()
        mock_doc.paragraphs = [mock_para, mock_para]
        mock_document.return_value = mock_doc

        result = _extract_text_from_docx("test.docx")
        self.assertIn("Paragraph 1", result)


class TestExtractTextFromPptx(unittest.TestCase):
    @patch('document_processor.Presentation')
    def test_pptx_success(self, mock_pres):
        mock_run = MagicMock()
        mock_run.text = "Slide text"
        
        mock_para = MagicMock()
        mock_para.runs = [mock_run]
        
        mock_frame = MagicMock()
        mock_frame.paragraphs = [mock_para]
        
        mock_shape = MagicMock()
        mock_shape.has_text_frame = True
        mock_shape.text_frame = mock_frame
        
        mock_slide = MagicMock()
        mock_slide.shapes = [mock_shape]
        
        mock_pres_instance = MagicMock()
        mock_pres_instance.slides = [mock_slide]
        mock_pres.return_value = mock_pres_instance

        result = _extract_text_from_pptx("test.pptx")
        self.assertIn("Slide text", result)

    @patch('document_processor.Presentation')
    def test_pptx_empty(self, mock_pres):
        mock_pres_instance = MagicMock()
        mock_pres_instance.slides = []
        mock_pres.return_value = mock_pres_instance

        result = _extract_text_from_pptx("test.pptx")
        self.assertEqual(result, "")


class TestExtractTextFromTxt(unittest.TestCase):
    @patch('builtins.open', new_callable=mock_open, read_data="Line 1\nLine 2\n")
    def test_txt_success(self, mock_file):
        result = _extract_text_from_txt("test.txt")
        self.assertIn("Line 1", result)
        self.assertIn("Line 2", result)


class TestCheckLlmServer(unittest.TestCase):
    @patch('document_processor.urllib.request.urlopen')
    def test_check_llm_server_success(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = b'{"model": "llama-3"}'
        mock_response.__enter__.return_value = mock_response
        mock_response.__exit__.return_value = None
        mock_urlopen.return_value = mock_response

        result = check_llm_server("http://localhost:1234/v1/models", "test-key")
        
        self.assertTrue(result)

    @patch('document_processor.socket.create_connection')
    @patch('document_processor.urllib.request.urlopen')
    def test_check_llm_server_connection_error(self, mock_urlopen, mock_socket):
        import urllib.error
        mock_urlopen.side_effect = urllib.error.URLError("Connection refused")
        mock_socket.side_effect = Exception("Socket connection failed")

        with self.assertRaises(ConnectionError) as cm:
            check_llm_server("http://localhost:1234/v1/models", "test-key")
        self.assertIn("Could not connect to LLM server", str(cm.exception))

    @patch('document_processor.socket.create_connection')
    @patch('document_processor.urllib.request.urlopen')
    def test_check_llm_server_timeout(self, mock_urlopen, mock_socket):
        import socket
        mock_urlopen.side_effect = socket.timeout()
        mock_socket.side_effect = socket.timeout()

        with self.assertRaises(ConnectionError) as cm:
            check_llm_server("http://localhost:1234/v1/models", "test-key")
        self.assertIn("Could not connect to LLM server", str(cm.exception))

    @patch('document_processor.socket.create_connection')
    @patch('document_processor.urllib.request.urlopen')
    def test_check_llm_server_http_error(self, mock_urlopen, mock_socket):
        import urllib.error
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="http://localhost:1234", code=500, msg="Server Error", hdrs={}, fp=None
        )
        mock_socket.return_value = MagicMock()

        result = check_llm_server("http://localhost:1234/v1/models", "test-key")
        
        self.assertTrue(result)


class TestExtractTextFromPdfEdgeCases(unittest.TestCase):
    @patch('builtins.open')
    @patch('document_processor.PyPDF2')
    def test_pdf_encrypted(self, mock_pypdf2, mock_open):
        mock_reader = MagicMock()
        mock_reader.is_encrypted = True
        mock_reader.decrypt.side_effect = Exception("Failed to decrypt")
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "Content after encryption issue"
        mock_reader.pages = [mock_page]
        mock_pypdf2.PdfReader.return_value = mock_reader

        from document_processor import extract_text_from_pdf
        result = extract_text_from_pdf("encrypted.pdf")
        self.assertIn("Content after encryption issue", result)

    @patch('builtins.open')
    @patch('document_processor.PyPDF2')
    def test_pdf_file_not_found(self, mock_pypdf2, mock_open):
        mock_open.side_effect = FileNotFoundError("File not found")

        from document_processor import extract_text_from_pdf
        with self.assertRaises(FileNotFoundError) as cm:
            extract_text_from_pdf("missing.pdf")
        self.assertIn("not found", str(cm.exception))


if __name__ == '__main__':
    unittest.main()
