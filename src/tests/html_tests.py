import unittest

import nurpg.html as html


class TestHtmlGeneration(unittest.TestCase):

    def test_generation(self):
        html_output = html.div(
            {'id': 'root'},
            html.span('testing'),
            html.p(
                'This is ',
                html.a(
                    {'href': '#link'},
                    'a link'
                ),
                '!'
            )
        )()

        self.assertEqual(html_output, '<div id="root"><span>testing</span><p>This is <a href="#link">a link</a>!</p></div>')

    def test_when_statements(self):
        true_partial = html.when(True).do('true').otherwise('false')
        self.assertEqual(('true',), true_partial.complete())

        false_partial = html.when(False).do('true').otherwise('false')
        self.assertEqual(('false',), false_partial.complete())

    def test_match_statements(self):
        match_partial = html.match('test', {
            'test': 'value',
            'test2': 12345
        })

        self.assertEqual('value', match_partial.complete())


if __name__ == '__main__':
    unittest.main()
