# -*- coding: utf-8 -*-
from __future__ import with_statement

import unittest
from os.path import join, dirname

from six import BytesIO
from six.moves.urllib.parse import quote

from hic_falcon_heavy.http.multipart_parser import MultiPartParser, MultiPartParserError
from hic_falcon_heavy.http.exceptions import RequestDataTooBig, TooManyFieldsSent
from hic_falcon_heavy.http.utils import parse_header_params


UNICODE_FILENAME = 'test-0123456789_中文_Orléans.jpg'


def get_contents(filename):
    with open(filename, 'rb') as f:
        return f.read()


class TestMultipartParser(unittest.TestCase):

    def test_limiting(self):
        payload = (
            b'--foo\r\nContent-Disposition: form-field; name=foo\r\n\r\n'
            b'Hello World\r\n'
            b'--foo\r\nContent-Disposition: form-field; name=bar\r\n\r\n'
            b'bar=baz\r\n--foo--'
        )

        parser = MultiPartParser(
            stream=BytesIO(payload),
            content_type='multipart/form-data; boundary=foo',
            content_length=len(payload),
            data_upload_max_memory_size=4
        )

        with self.assertRaises(RequestDataTooBig):
            parser.parse()

        parser = MultiPartParser(
            stream=BytesIO(payload),
            content_type='multipart/form-data; boundary=foo',
            content_length=len(payload),
            data_upload_max_memory_size=400
        )

        form, _ = parser.parse()
        self.assertEqual(u'Hello World', form['foo'].value)

        parser = MultiPartParser(
            stream=BytesIO(payload),
            content_type='multipart/form-data; boundary=foo',
            content_length=len(payload),
            data_upload_max_number_fields=1
        )

        with self.assertRaises(TooManyFieldsSent):
            parser.parse()

        payload = (
            b'--foo\r\nContent-Disposition: form-field; name=foo\r\n\r\n'
            b'Hello World\r\n'
            b'--foo\r\nContent-Disposition: form-field; name=bar; filename=Grateful Dead\r\n\r\n'
            b'aoxomoxoa\r\n--foo--'
        )

        parser = MultiPartParser(
            stream=BytesIO(payload),
            content_type='multipart/form-data; boundary=foo',
            content_length=len(payload),
            data_upload_max_memory_size=4
        )

        with self.assertRaises(RequestDataTooBig):
            parser.parse()

    def test_missing_multipart_boundary(self):
        with self.assertRaises(MultiPartParserError) as ctx:
            MultiPartParser(
                stream=BytesIO(''),
                content_type='multipart/form-data',
                content_length=0
            )

        self.assertIn("Invalid boundary in multipart", ctx.exception.message)

    def test_invalid_multipart_content(self):
        payload = b'bar'

        parser = MultiPartParser(
            stream=BytesIO(payload),
            content_type='multipart/form-data; boundary="foo"',
            content_length=len(payload)
        )

        with self.assertRaises(MultiPartParserError) as ctx:
            parser.parse()

        self.assertEqual("Expected boundary at start of multipart data", ctx.exception.message)

    def test_empty_content(self):
        parser = MultiPartParser(
            stream=BytesIO(b''),
            content_type='multipart/form-data; boundary=foo',
            content_length=0
        )

        form, files = parser.parse()
        self.assertEqual(0, len(form))
        self.assertEqual(0, len(files))

    def test_invalid_content_length(self):
        with self.assertRaises(MultiPartParserError) as ctx:
            MultiPartParser(
                stream=BytesIO(b''),
                content_type='multipart/form-data; boundary=foo',
                content_length=-1
            )

        self.assertIn("Invalid content length", ctx.exception.message)

    def test_basic(self):
        resources = join(dirname(__file__), 'multipart')

        repository = (
            ('firefox3-2png1txt', '---------------------------186454651713519341951581030105', (
                (u'anchor.png', 'file1', 'image/png', 'file1.png'),
                (u'application_edit.png', 'file2', 'image/png', 'file2.png')
            ), u'example text'),
            ('firefox3-2pnglongtext', '---------------------------14904044739787191031754711748', (
                (u'accept.png', 'file1', 'image/png', 'file1.png'),
                (u'add.png', 'file2', 'image/png', 'file2.png')
            ), u'--long text\r\n--with boundary\r\n--lookalikes--'),
            ('opera8-2png1txt', '----------zEO9jQKmLc2Cq88c23Dx19', (
                (u'arrow_branch.png', 'file1', 'image/png', 'file1.png'),
                (u'award_star_bronze_1.png', 'file2', 'image/png', 'file2.png')
            ), u'blafasel öäü'),
            ('webkit3-2png1txt', '----WebKitFormBoundaryjdSFhcARk8fyGNy6', (
                (u'gtk-apply.png', 'file1', 'image/png', 'file1.png'),
                (u'gtk-no.png', 'file2', 'image/png', 'file2.png')
            ), u'this is another text with ümläüts'),
            ('ie6-2png1txt', '---------------------------7d91b03a20128', (
                (u'file1.png', 'file1', 'image/x-png', 'file1.png'),
                (u'file2.png', 'file2', 'image/x-png', 'file2.png')
            ), u'ie6 sucks :-/')
        )

        for name, boundary, files, text in repository:
            folder = join(resources, name)
            payload = get_contents(join(folder, 'request.txt'))
            for filename, field, content_type, fsname in files:
                parser = MultiPartParser(
                    stream=BytesIO(payload),
                    content_type='multipart/form-data; boundary="%s"' % boundary,
                    content_length=len(payload)
                )

                form, files = parser.parse()

                if filename:
                    self.assertEqual(filename, files[field].filename)
                    self.assertEqual(content_type, files[field].content_type)
                    self.assertEqual(get_contents(join(folder, fsname)), files[field].stream.read())
                else:
                    self.assertEqual(filename, form[field].filename)
                    self.assertEqual(content_type, form[field].content_type)
                    self.assertEqual(get_contents(join(folder, fsname)), form[field])

    def test_ie7_unc_path(self):
        payload_file = join(dirname(__file__), 'multipart', 'ie7_full_path_request.txt')
        payload = get_contents(payload_file)
        boundary = '---------------------------7da36d1b4a0164'

        parser = MultiPartParser(
            stream=BytesIO(payload),
            content_type='multipart/form-data; boundary="%s"' % boundary,
            content_length=len(payload)
        )

        form, files = parser.parse()

        self.assertEqual(u'Sellersburg Town Council Meeting 02-22-2010doc.doc',
                         files['cb_file_upload_multiple'].filename)

    def test_end_of_file(self):
        payload = (
            b'--foo\r\n'
            b'Content-Disposition: form-data; name="test"; filename="test.txt"\r\n'
            b'Content-Type: text/plain\r\n\r\n'
            b'file contents and no end'
        )

        parser = MultiPartParser(
            stream=BytesIO(payload),
            content_type='multipart/form-data; boundary=foo',
            content_length=len(payload)
        )

        with self.assertRaises(MultiPartParserError) as ctx:
            parser.parse()

        self.assertEqual(u'Unexpected end of part', ctx.exception.message)

    def test_broken_base64(self):
        payload = (
            '--foo\r\n'
            'Content-Disposition: form-data; name="test"; filename="test.txt"\r\n'
            'Content-Transfer-Encoding: base64\r\n'
            'Content-Type: text/plain\r\n\r\n'
            'error'
            '--foo--'
        )

        parser = MultiPartParser(
            stream=BytesIO(payload),
            content_type='multipart/form-data; boundary=foo',
            content_length=len(payload)
        )

        with self.assertRaises(MultiPartParserError) as ctx:
            parser.parse()

        self.assertIn(u'Could not decode base64 data', ctx.exception.message)

    def test_file_no_content_type(self):
        payload = (
            b'--foo\r\n'
            b'Content-Disposition: form-data; name="test"; filename="test.txt"\r\n\r\n'
            b'file contents\r\n--foo--'
        )

        parser = MultiPartParser(
            stream=BytesIO(payload),
            content_type='multipart/form-data; boundary=foo',
            content_length=len(payload)
        )

        _, files = parser.parse()

        self.assertEqual(u'test.txt', files['test'].filename)
        self.assertEqual(b'file contents', files['test'].stream.read())

    def test_extra_newline(self):
        payload = (
            b'\r\n\r\n--foo\r\n'
            b'Content-Disposition: form-data; name="foo"\r\n\r\n'
            b'a string\r\n'
            b'--foo--'
        )

        parser = MultiPartParser(
            stream=BytesIO(payload),
            content_type='multipart/form-data; boundary=foo',
            content_length=len(payload)
        )

        form, _ = parser.parse()

        self.assertEqual(u'a string', form['foo'].value)

    def test_headers(self):
        payload = (
            b'--foo\r\n'
            b'Content-Disposition: form-data; name="foo"; filename="foo.txt"\r\n'
            b'X-Custom-Header: blah\r\n'
            b'Content-Type: text/plain; charset=utf-8\r\n\r\n'
            b'file contents, just the contents\r\n'
            b'--foo--'
        )

        parser = MultiPartParser(
            stream=BytesIO(payload),
            content_type='multipart/form-data; boundary=foo',
            content_length=len(payload)
        )

        _, files = parser.parse()

        self.assertEqual('text/plain', files['foo'].mimetype)
        self.assertEqual({'charset': 'utf-8'}, files['foo'].mimetype_params)
        self.assertEqual('text/plain; charset=utf-8', files['foo'].content_type)
        self.assertEqual(files['foo'].content_type, files['foo'].headers['content-type'])
        self.assertEqual('blah', files['foo'].headers['x-custom-header'])

        payload = (
            b'--foo\r\n'
            b'Content-Disposition: form-data; name="foo"\r\n'
            b'X-Custom-Header: blah\r\n'
            b'Content-Type: application/json; charset=utf-8\r\n\r\n'
            b'314\r\n'
            b'--foo--'
        )

        parser = MultiPartParser(
            stream=BytesIO(payload),
            content_type='multipart/form-data; boundary=foo',
            content_length=len(payload)
        )

        form, _ = parser.parse()

        self.assertEqual('314', form['foo'].value)
        self.assertEqual('application/json', form['foo'].mimetype)
        self.assertEqual({'charset': 'utf-8'}, form['foo'].mimetype_params)
        self.assertEqual('application/json; charset=utf-8', form['foo'].content_type)
        self.assertEqual(form['foo'].content_type, form['foo'].headers['content-type'])
        self.assertEqual('blah', form['foo'].headers['x-custom-header'])

    def test_empty_multipart(self):
        payload = b'--boundary--'

        parser = MultiPartParser(
            stream=BytesIO(payload),
            content_type='multipart/form-data; boundary=boundary',
            content_length=len(payload)
        )

        form, files = parser.parse()

        self.assertEqual(0, len(form))
        self.assertEqual(0, len(files))

    def test_unicode_file_name_rfc2231(self):
        """
        Test receiving file upload when filename is encoded with RFC2231
        (#22971).
        """
        payload = (
            b'--foo\r\n'
            b'Content-Disposition: form-data; name="file_unicode"; filename*=UTF-8\'\'{}\r\n'
            b'Content-Type: application/octet-stream\r\n\r\n'
            b'You got pwnd.\r\n'
            b'\r\n--foo--\r\n'
        ).format(quote(UNICODE_FILENAME))

        parser = MultiPartParser(
            stream=BytesIO(payload),
            content_type='multipart/form-data; boundary="foo"',
            content_length=len(payload)
        )

        _, files = parser.parse()

        self.assertEqual(UNICODE_FILENAME.decode('utf-8'), files['file_unicode'].filename)

    def test_rfc2231_unicode_name(self):
        """
        Test receiving file upload when filename is encoded with RFC2231
        (#22971).
        """
        payload = (
            b'--foo\r\n'
            b'Content-Disposition: form-data; name*=UTF-8\'\'file_unicode; filename*=UTF-8\'\'{}\r\n'
            b'Content-Type: application/octet-stream\r\n\r\n'
            b'You got pwnd.\r\n'
            b'\r\n--foo--\r\n'
        ).format(quote(UNICODE_FILENAME))

        parser = MultiPartParser(
            stream=BytesIO(payload),
            content_type='multipart/form-data; boundary="foo"',
            content_length=len(payload)
        )

        _, files = parser.parse()

        self.assertEqual(UNICODE_FILENAME.decode('utf-8'), files['file_unicode'].filename)

    def test_blank_filenames(self):
        """
        Receiving file upload when filename is blank (before and after
        sanitization) should be okay.
        """
        # The second value is normalized to an empty name by
        # MultiPartParser.IE_sanitize()
        filenames = ['', 'C:\\Windows\\']

        payload = b''
        for i, name in enumerate(filenames):
            payload += (
                b'--foo\r\n'
                b'Content-Disposition: form-data; name="file{}"; filename="{}"\r\n'
                b'Content-Type: application/octet-stream\r\n\r\n'
                b'You got pwnd.\r\n'
            ).format(i, name)

        payload += b'\r\n--foo--\r\n'

        parser = MultiPartParser(
            stream=BytesIO(payload),
            content_type='multipart/form-data; boundary="foo"',
            content_length=len(payload)
        )

        _, files = parser.parse()

        self.assertEqual(0, len(files))

    def test_dangerous_file_names(self):
        """Uploaded file names should be sanitized before ever reaching the view."""
        # This test simulates possible directory traversal attacks by a
        # malicious uploader We have to do some monkeybusiness here to construct
        # a malicious payload with an invalid file name (containing os.sep or
        # os.pardir). This similar to what an attacker would need to do when
        # trying such an attack.
        scary_file_names = [
            "/tmp/hax0rd.txt",  # Absolute path, *nix-style.
            "C:\\Windows\\hax0rd.txt",  # Absolute path, win-style.
            "C:/Windows/hax0rd.txt",  # Absolute path, broken-style.
            "\\tmp\\hax0rd.txt",  # Absolute path, broken in a different way.
            "/tmp\\hax0rd.txt",  # Absolute path, broken by mixing.
            "subdir/hax0rd.txt",  # Descendant path, *nix-style.
            "subdir\\hax0rd.txt",  # Descendant path, win-style.
            "sub/dir\\hax0rd.txt",  # Descendant path, mixed.
            "../../hax0rd.txt",  # Relative path, *nix-style.
            "..\\..\\hax0rd.txt",  # Relative path, win-style.
            "../..\\hax0rd.txt"  # Relative path, mixed.
        ]

        payload = b''
        for i, name in enumerate(scary_file_names):
            payload += (
                b'--foo\r\n'
                b'Content-Disposition: form-data; name="file{}"; filename="{}"\r\n'
                b'Content-Type: application/octet-stream\r\n\r\n'
                b'You got pwnd.\r\n'
            ).format(i, name)

        payload += b'\r\n--foo--\r\n'

        parser = MultiPartParser(
            stream=BytesIO(payload),
            content_type='multipart/form-data; boundary="foo"',
            content_length=len(payload)
        )

        _, files = parser.parse()

        # The filenames should have been sanitized by the time it got to the view.
        for i, name in enumerate(scary_file_names):
            got = files['file%s' % i]
            self.assertEqual('hax0rd.txt', got.filename)

    def test_filename_overflow(self):
        """File names over 256 characters (dangerous on some platforms) get fixed up."""
        long_str = 'f' * 300
        cases = [
            # field name, filename, expected
            ('long_filename', '%s.txt' % long_str, '%s.txt' % long_str[:251]),
            ('long_extension', 'foo.%s' % long_str, '.%s' % long_str[:254]),
            ('no_extension', long_str, long_str[:255]),
            ('no_filename', '.%s' % long_str, '.%s' % long_str[:254]),
            ('long_everything', '%s.%s' % (long_str, long_str), '.%s' % long_str[:254]),
        ]

        payload = b''
        for name, filename, _ in cases:
            payload += (
                b'--foo\r\n'
                b'Content-Disposition: form-data; name="{}"; filename="{}"\r\n'
                b'Content-Type: application/octet-stream\r\n\r\n'
                b'Oops.\r\n'
            ).format(name, filename)

        payload += b'\r\n--foo--\r\n'

        parser = MultiPartParser(
            stream=BytesIO(payload),
            content_type='multipart/form-data; boundary="foo"',
            content_length=len(payload)
        )

        _, files = parser.parse()

        for name, _, expected in cases:
            got = files[name]
            self.assertEqual(expected, got.filename, 'Mismatch for {}'.format(name))
            self.assertLess(len(got.filename), 256,
                            "Got a long file name (%s characters)." % len(got.filename))

    def test_rfc2231_parsing(self):
        test_data = (
            (b"Content-Type: application/x-stuff; title*=us-ascii'en-us'This%20is%20%2A%2A%2Afun%2A%2A%2A",
             u"This is ***fun***"),
            (b"Content-Type: application/x-stuff; title*=UTF-8''foo-%c3%a4.html",
             u"foo-ä.html"),
            (b"Content-Type: application/x-stuff; title*=iso-8859-1''foo-%E4.html",
             u"foo-ä.html"),
        )
        for raw_line, expected_title in test_data:
            parsed = parse_header_params(raw_line)
            self.assertEqual(parsed[1]['title'], expected_title)

    def test_rfc2231_wrong_title(self):
        """
        Test wrongly formatted RFC 2231 headers (missing double single quotes).
        Parsing should not crash (#24209).
        """
        test_data = (
            (b"Content-Type: application/x-stuff; title*='This%20is%20%2A%2A%2Afun%2A%2A%2A",
             b"'This%20is%20%2A%2A%2Afun%2A%2A%2A"),
            (b"Content-Type: application/x-stuff; title*='foo.html",
             b"'foo.html"),
            (b"Content-Type: application/x-stuff; title*=bar.html",
             b"bar.html"),
        )
        for raw_line, expected_title in test_data:
            parsed = parse_header_params(raw_line)
            self.assertEqual(parsed[1]['title'], expected_title)


if __name__ == '__main__':
    unittest.main()
