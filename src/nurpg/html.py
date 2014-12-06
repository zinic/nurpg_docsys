import copy
import types
import inspect
import collections


_CALL_ATTR = '__call__'

_TAGS = list()
_TAG_NAMES = [
    'html',
    'head',
    'title',
    'base',
    'link',
    'meta',
    'style',
    'script',
    'noscript',
    'template',
    'body',
    'section',
    'nav',
    'article',
    'aside',
    'h1',
    'h2',
    'h3',
    'h4',
    'h5',
    'h6',
    'header',
    'footer',
    'address',
    'main',
    'p',
    'hr',
    'pre',
    'blockquote',
    'ol',
    'ul',
    'li',
    'dl',
    'dt',
    'dd',
    'figure',
    'figcaption',
    'div',
    'a',
    'em',
    'strong',
    'small',
    's',
    'cite',
    'q',
    'dfn',
    'abbr',
    'data',
    'time',
    'code',
    'var',
    'samp',
    'kbd',
    'sub',
    'sup',
    'i',
    'b',
    'u',
    'mark',
    'ruby',
    'rt',
    'rp',
    'bdi',
    'bdo',
    'span',
    'br',
    'wbr',
    'ins',
    'del',
    'img',
    'iframe',
    'embed',
    'object',
    'param',
    'video',
    'audio',
    'source',
    'track',
    'canvas',
    'map',
    'area',
    'svg',
    'math',
    'tabe',
    'caption',
    'colgroup',
    'col',
    'tbody',
    'thead',
    'tfoot',
    'tr',
    'td',
    'th',
    'form',
    'fieldset',
    'legend',
    'label',
    'input',
    'button',
    'select',
    'datalist',
    'optgroup',
    'option',
    'textarea',
    'keygen',
    'output',
    'progress',
    'meter',
    'details',
    'summary',
    'menuitem',
    'menu',
]


class Partial(object):

    def complete(self):
        raise NotImplementedError()


class PartialGenerator(object):

    def prime(self, **kwargs):
        raise NotImplementedError()


class HtmlTag(PartialGenerator):

    def __init__(self, tag):
        self.name = tag
        self._template = '<' + tag + '{attributes}>{content}</' + tag + '>'

    def prime(self, *args):
        attrs = dict()
        contents = list()

        for arg in args:
            if _is_attr_dict(arg):
                attrs.update(arg)
            else:
                contents.append(arg)

        return HtmlPartial(self._template, attrs, contents).complete


class HtmlPartial(Partial):

    def __init__(self, template, attrs=None, contents=None):
        self._template = template

        self.attrs = attrs or dict()
        self.contents = contents or list()

    def complete(self):
        # Copy the contents so we don't damage the original datastructure
        op_stack = copy.copy(self.contents)

        # Reverse the copy of the contents list to make it into our contents
        # stack!
        op_stack.reverse()

        # Capture vars
        results = list()
        attrs = copy.copy(self.attrs)

        # Keep going until there aren't any more ops left
        while len(op_stack) > 0:
            next_op = op_stack.pop()

            if next_op is None:
                # A None next_op value is a noop
                continue

            if _callable(next_op):
                # Reduce this op and re-eval it
                op_stack.append(next_op())
            elif isinstance(next_op, Partial):
                # Complete any partials we encounter
                op_stack.append(next_op.complete())
            elif _is_attr_dict(next_op):
                # Extend our attributes
                attrs.update(next_op)
            elif _should_iterate(next_op):
                if isinstance(next_op, types.GeneratorType):
                    # Execute the generator, store and then flip its results
                    op_stack.extend(reversed([op for op in next_op]))
                else:
                    # Append and reduce additional components
                    op_stack.extend(reversed(next_op))
            else:
                # All other nodes are appended
                results.append(next_op if type(next_op) is str else str(next_op))

        # Unpack attributes
        attr_str = ''
        if len(attrs) > 0:
            attr_str = ''.join([' {}="{}"'.format(k, v)
                 for k, v in attrs.iteritems()])

        # Return our formatted template
        return self._template.format(
            attributes=attr_str,
            content=''.join(results))


class MatchPartial(Partial):

    def __init__(self, matches, default, lookup):
        self._matches = matches or dict()
        self._default = default
        self._lookup = lookup

    def complete(self):
        return self._matches.get(self._lookup, self._default)


class WhenPartial(Partial):

    def __init__(self, condition):
        self._condition = condition

        self._on_false = None
        self._on_true = None

    def do(self, *args):
        # If the condition results in a boolean true evaluation then this
        # result is what should be returned.
        self._on_true = args
        return self

    def otherwise(self, *args):
        # If the condition results in a boolean false evaluation then this
        # result is what should be returned.
        self._on_false = args
        return self

    def complete(self):
        arg_eval = None

        if _callable(self._condition):
            # The condition is a function that will tell us what the eval
            # should be and the args pass to complete are the arguments to
            # that function
            arg_eval = self._condition()
        else:
            # The condition is a constnat perhaps
            arg_eval = self._condition

        # Return either result based on our evaluation
        return self._on_true if arg_eval else self._on_false


class HtmlAttributePartial(Partial):

    def __init__(self, name, value):
        self._name = name
        self._value = value

    def complete(self):
        return { self._name: self._value }


class DocumentObjectPartial(Partial):

    def __init__(self, doc, delegate):
        self._doc = doc
        self._delegate = delegate

    def complete(self):
        return self._delegate(self._doc)


def defer(node, delegate):
    return DocumentObjectPartial(node, delegate)


def attribute(name, value):
    return HtmlAttributePartial(name, value)


def id_attr(value):
    return attribute('id', value)


def style_attr(value):
    return attribute('style', value)


def match(lookup, matches, default=None):
    return MatchPartial(matches, default, lookup)


def when(condition):
    return WhenPartial(condition)


def _callable(obj):
    return hasattr(obj, _CALL_ATTR)


def _is_attr_dict(obj):
    return isinstance(obj, dict)


def _should_iterate(obj):
    return not _is_str(obj) and isinstance(obj, collections.Iterable)


def _is_str(obj):
    return isinstance(obj, str)


# Init our tag functions
for tag_name in _TAG_NAMES:
    _TAGS.append(HtmlTag(tag_name))
    vars()[tag_name] = _TAGS[len(_TAGS) - 1].prime
