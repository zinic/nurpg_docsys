import os
import uuid
import logging

import nurpg.error as error


# Logging!
_LOG = logging.getLogger(__name__)

# Constants
MAX_DOC_SIZE_MB = 16
MB_IN_BYTES = 1048576L

# Word list
D_WORDS = [
    'root',
    'title',
    'difficulty',
    'grants',
    'author',
    'date',
    'content',
    'mechanic',
    'note',
    'effect',
    'requires',
    'cost',
    'ability',
    'section',
    'feature',
    'ref',
    'aspect',
    'halt'
]

# Words that may contain other words
D_ELEMENTS = [
    'section',
    'aspect',
    'feature',
    'mechanic',
    'effect',
    'ability',
    'aspect'
]

# Set reserved words
for word in D_WORDS:
    name = 'D_{}'.format(word.upper())
    vars()[name] = word

# Token type identifiers
CONTENT_TOKEN = 'content'
DIRECTIVE_TOKEN = 'directive'

# Directive statement start and end characters
DIRECTIVE_CH = '@'
DIRECTIVE_END_CH = '\n'

# Escape character to use
ESCAPE_CH = '\\'

# Whitespace characters
WHITE_SPACE = [ ' ', '\r', '\n', 't' ]

# Token states
TK_START = 1
TK_CONTENT = 2
TK_DIRECTIVE = 3

# Parser states
ST_NEXT = 0
ST_WANTS_CONTENT = 1


class DocumentError(error.ErrorMessage):
    pass


class DocumentParsingError(DocumentError):
    pass


class DocumentContext(object):

    def __init__(self, filename):
        self.filename = filename
        self._doc_ref = None

    def __enter__(self):
        if not os.path.exists(self.filename):
            raise DocumentError('File {} not found!'.format(self.filename))

        if  os.path.getsize(self.filename) >= (MAX_DOC_SIZE_MB * MB_IN_BYTES):
            raise DocumentError('File is too large to read. Maximum file  size'
                                ' supported is {} MB.'.format(MAX_DOC_SIZE_MB))

        self._doc_ref = _open(self.filename)
        return self._doc_ref

    def __exit__(self, type, value, traceback):
        write(self._doc_ref, self.filename)


class DocumentNode(object):

    def __init__(self, kind=None, content=None):
        self.id = str(uuid.uuid4())
        self.kind = kind
        self.parent = None
        self.content = content
        self._children = list()

    @property
    def children(self):
        return self._children

    def append(self, child_element):
        # Let the child know that we're its parent
        child_element.parent = self

        # Actually link it
        self._children.append(child_element)

    def find(self, kind, content=None):
        return find(self, kind, content)

    def __str__(self):
        str_content = ''

        if self.kind is not None:
            str_content += '{}{}'.format(DIRECTIVE_CH, escape_str(self.kind))

            if self.content is not None:
                str_content += ' {}'.format(escape_str(self.content))

            str_content += '{}'.format(DIRECTIVE_END_CH)

        return str_content


class Document(object):

    def __init__(self):
        self.root = DocumentNode(D_ROOT, '')
        self.title = None
        self.authors = list()

    @property
    def sections(self):
        for sec in find(self.root, D_SECTION):
            yield sec


class DocumentBuilder(object):

    def __init__(self, root):
        self._doc = Document()

        self._build_stack = list()
        self._current = self._doc.root

    @property
    def document(self):
        return self._doc

    @property
    def current_kind(self):
        return self._current.kind

    def add_author(self, author_info):
        # Append the new author
        self._doc.authors.append(author_info)
        self._doc.root.append(DocumentNode(D_AUTHOR, author_info))

    def set_title(self, title_content):
        if self._doc.title is not None:
            raise DocumentError('Document has two title nodes.')

        # Append and set the title
        self._doc.title = title_content
        self._doc.root.append(DocumentNode(D_TITLE, title_content))

    def append_node(self, node):
        self._current.append(node)

    def enter(self, node):
        # Append to the current document node and get the new object ref
        self.append_node(node)

        # Drop this node and descend into the next object
        self._build_stack.append(self._current)
        self._current = node

    def exit(self):
        # Deref the current object and move to what's on the stack
        self._current = self._build_stack.pop()

    def exit_if(self, *args):
        if self._current.kind in args:
            self.exit()

    def exit_to(self, kind):
        while self._current.kind != kind:
            self.exit()


class Token(object):

    def __init__(self, kind):
        self.kind = kind


class ContentToken(Token):

    def __init__(self, content):
        super(ContentToken, self).__init__(CONTENT_TOKEN)
        self.content = content

    def __str__(self):
        return 'Content Token: {}'.format(self.content)


class DirectiveToken(Token):

    def __init__(self, directive, arguments=None):
        super(DirectiveToken, self).__init__(DIRECTIVE_TOKEN)
        self.directive = directive
        self.arguments = arguments or ''

    def __str__(self):
        return 'Command Token: {}, Args: {}'.format(
            self.directive, self.arguments)


def escape_str(source):
    return source.replace('\\', '\\\\').replace('|', '\\|')


def edit(doc_filename):
    return DocumentContext(doc_filename)


def write(document, doc_filename):
    with open(doc_filename, 'w') as fout:
        for node in document:
            node_contents = str(node)
            fout.write(str(node_contents))


def read(doc_filename):
    if not os.path.exists(doc_filename):
        raise DocumentError('File {} not found!'.format(doc_filename))

    if  os.path.getsize(doc_filename) >= (MAX_DOC_SIZE_MB * MB_IN_BYTES):
        raise DocumentError('File is too large to read. Maximum file  size'
                            ' supported is {} MB.'.format(MAX_DOC_SIZE_MB))

    document = None
    doc_contents = _read_file(doc_filename)

    if doc_contents is not None:
        _LOG.info('Read {} Bytes.\n'.format(len(doc_contents)))
        document = _parse(doc_contents)

    return document


def find(root, kind, content=None):
    cursor_stack = [(0, root)]

    while len(cursor_stack) > 0:
        # Unpack where we left off
        cursor_idx, next_obj = cursor_stack.pop()

        if cursor_idx < len(next_obj.children):
            # Push where we want to pick up next
            cursor_stack.append((cursor_idx + 1, next_obj))

            # Pick up the child node of interest
            node = next_obj.children[cursor_idx]

            # Is the node the kind that we're looking for?
            if node.kind == kind:
                # Filter if we're trying to match content too
                if content is not None:
                    if content == node.content:
                        yield node
                else:
                    yield node

            # Does the node have children to iterate through?
            if len(node.children) > 0:
                cursor_stack.append((0, node))

        # In the case where we run out of children we simply pass through
        # and iterate through the loop


def _matches_spec(node, node_spec, case_insensitive):
    content = node.content or ''
    formatted = content if not case_insensitive else content.lower()

    return fnmatch.fnmatchcase(formatted, node_spec)


def _parse(content):
    doc_builder = DocumentBuilder(DocumentNode(D_ROOT, ''))

    for node in _tokenize_content(content):
        if node.kind == D_SECTION:
            # Jump all the way back to the root
            doc_builder.exit_to(D_ROOT)
            doc_builder.enter(node)
        elif node.kind == D_FEATURE:
            # Jump to the parent section
            doc_builder.exit_to(D_SECTION)
            doc_builder.enter(node)
        elif node.kind == D_EFFECT:
            # Jump to the parent section
            doc_builder.exit_to(D_SECTION)
            doc_builder.enter(node)
        elif node.kind == D_ABILITY:
            # Jump to the parent section
            doc_builder.exit_to(D_SECTION)
            doc_builder.enter(node)
        elif node.kind == D_ASPECT:
            # Jump to the parent section
            doc_builder.exit_to(D_SECTION)
            doc_builder.enter(node)
        elif node.kind == D_MECHANIC:
            # Exit if this is another mechanic in a series
            doc_builder.exit_if(D_MECHANIC)
            doc_builder.enter(node)
        elif node.kind == D_AUTHOR:
            # Add this author to the list of authors
            doc_builder.add_author(node.content)
        elif node.kind == D_TITLE:
            # Set the title of the document
            doc_builder.set_title(node.content)
        else:
            # Simply append this node in-place
            doc_builder.append_node(node)

    # Return to the root and then return the built document
    doc_builder.exit_to(D_ROOT)
    return doc_builder.document


def _tokenize_content(content):
    state = ST_NEXT

    for token in _tokenize(content):
        node = None

        if token.kind == DIRECTIVE_TOKEN:
            if token.directive == D_HALT:
                # Halt processing of the content
                break
            elif token.directive in D_WORDS:
                node = DocumentNode(token.directive, token.arguments)
            else:
                # Don't know this command chief
                raise DocumentParsingError('Unknown directive: {}'.format(
                    token.directive))
        else:
            node = DocumentNode(D_CONTENT, token.content)

        # If a node has been set, save it to our list of nodes that represents
        # the document
        if node is not None:
            yield node


def _tokenize(content):
    ch_buff = ''
    state = TK_START
    escaped = False

    for next_ch in content:
        token = None

        if state == TK_START:
            state = TK_CONTENT

        if state == TK_CONTENT:
            if escaped:
                ch_buff += next_ch
                escaped = False
            else:
                if next_ch == DIRECTIVE_CH:
                    token = _parse_content(ch_buff)

                    state = TK_DIRECTIVE
                    ch_buff = ''
                elif next_ch == ESCAPE_CH:
                    escaped = True
                else:
                    ch_buff += next_ch

        elif state == TK_DIRECTIVE:
            if next_ch == DIRECTIVE_END_CH:
                token = _parse_directive(ch_buff)

                state = TK_CONTENT
                ch_buff = ''
            else:
                ch_buff += next_ch

        if token is not None:
            yield token

    if state == TK_CONTENT:
        if len(ch_buff) > 0:
            yield _parse_content(ch_buff)
    else:
        raise DocumentParsingError('Illegal end state for parsing: {}'.format(
            state))


def _parse_content(content):
    clean_content = content.strip()

    if len(clean_content) > 0:
        return ContentToken(clean_content)
    return None


def _parse_directive(content):
    split_content = content.split(' ', 1)

    if len(split_content) == 1:
        return DirectiveToken(split_content[0])
    else:
        return DirectiveToken(split_content[0], split_content[1])


def _read_file(filename):
    try:
        with open(filename, 'r') as fin:
            return fin.read()
    except OSError as ex:
        _LOG.error('Failed to read document file {}.'.format(doc_filename))
        _LOG.exception(ex)

    return None
