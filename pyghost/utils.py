import re


def trim_xml_html_tags(data_str):
    """
    Trim all HTML/XML tags and replace the special "panel" tag with a new line
    :param data_str: input data string to trim
    :return: Trimmed string

    >>> trim_xml_html_tags('')
    ''
    >>> trim_xml_html_tags(u'')
    ''
    >>> trim_xml_html_tags(u'hello world')
    'hello world'
    >>> trim_xml_html_tags('hello world')
    'hello world'
    >>> trim_xml_html_tags('<h1>hello world</h1>')
    'hello world'
    >>> trim_xml_html_tags('<div><h1>hello world!</h1></div><div class="panel panel-default">:)')
    'hello world!\\n:)'
    """
    return re.sub('<[^<]+?>', '', data_str.replace('</div><div class="panel panel-default">', "\n"))


def trim_ansi_tags(data_str):
    """
    Trim all ANSI tags
    :param data_str: input data string to trim
    :return: Trimmed string

    >>> trim_ansi_tags('')
    ''
    >>> trim_ansi_tags(u'')
    ''
    >>> trim_ansi_tags(u'hello world')
    'hello world'
    >>> trim_ansi_tags('hello world')
    'hello world'
    >>> trim_ansi_tags(u'hello world'.encode('utf-8'))
    'hello world'
    >>> trim_ansi_tags('2019/02/11 09:34:37 GMT: \x1B[32mSTATE: Started\x1B[0m')
    '2019/02/11 09:34:37 GMT: STATE: Started'
    >>> trim_ansi_tags('2019/02/11 09:34:37 GMT: \x1B[32mSTATE: Started\x1B[0m'.encode('utf-8'))
    '2019/02/11 09:34:37 GMT: STATE: Started'
    """
    # Remove ANSI escape sequences
    # https://stackoverflow.com/questions/14693701/how-can-i-remove-the-ansi-escape-sequences-from-a-string-in-python
    return re.sub(r'\x1B\[[0-?]*[ -/]*[@-~]', '', data_str.decode('utf-8'))
