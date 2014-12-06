import os
import re
import sys
import fnmatch
import logging
import readline
import tempfile
import subprocess

import nurpg.html as html
import nurpg.error as error
import nurpg.config as config
import nurpg.output as output
import nurpg.document as document

from nurpg.compat import user_input


# Relevant ENV variables
_EDITOR_ENV_KEY = 'EDITOR'

# Name specifier regex
_NAME_REGEX = re.compile('^([^\($]+)(?:\(([^\)]+)\))?$')

# Regex for parsing grant statements
_GRANT_REGEX = re.compile('^([^\s]+)\s([^,(]+)(?:\(([^)]+)\))?(?:\,\s?(\d+))?$')


def tool_functions():
    return  {
        'init': init_tool,
        'export': export_tool,
        'status': status_tool,
        'find': find_tool,
        'add': add_tool,
        'stash': stash_tool
    }


class ToolError(error.ErrorMessage):

    def __init__(self, msg='', errno=error.GENERAL_FAILURE, cause=None):
        super(ToolError, self).__init__(msg)

        self.errno = errno
        self.cause = cause

    @classmethod
    def wrap(cls, ex, errno=error.GENERAL_FAILURE):
        msg = str(ex)

        if hasattr(ex, 'msg'):
            msg = getattr(ex, 'msg')

        raise ToolError(msg, errno, ex)


def has_arguments(node):
    node_not_none = node is not None
    node_has_arguments = node.arguments is not None

    return node_not_none and node_has_arguments


def init_tool(args):
    output.console('Writing document confniguration.')

    try:
        # Attempt to initialize a new configuration
        config.init_config(args.document)

        # If we get here we're a-okay
        output.console('Initialization OK.')
    except Exception as ex:
        ToolError.wrap(ex)


_CSS_TOP_GAP = html.style_attr('padding-top: 15px;')
_CSS_TOP_GAP_SMALL = html.style_attr('padding-top: 5px;')
_CSS_BOLD = html.style_attr('font-weight: bold;')
_NOTE_HCLS = html.attribute('class', 'note')
_BR = html.br()()


def format_content(content):
    return content.replace('\n\n', _BR).replace('\n', _BR)


def render_mechanic(doc, mechanic):
    yield html.style_attr('font-size: 10pt;')
    yield html.div(
        html.id_attr(mechanic.id),
        html.style_attr('font-size: 10pt;'),

        html.span(
            # Make sure the text is bold
            html.style_attr('font-weight: bold;'),
            'Feature Mechanic: '
        ),
        html.span(format_name(mechanic.content)))

    for child in mechanic.children:
        if child.kind == document.D_COST:
            yield html.div(
                html.style_attr('font-size: 10pt;'),

                html.span(
                    # Make sure the text is bold
                    html.style_attr('font-weight: bold;'),

                    'Aspect Point {}: '.format(
                        'Cost' if int(child.content) >= 0 else 'Return')
                ),

                html.span(child.content))

        else:
            yield html.p(
                html.style_attr('font-size: 10pt;'),
                format_content(child.content))


def render_feature(doc, feature):
    yield html.div(
        html.id_attr(feature.id),
        html.h4(format_name(feature.content)))

    for child in feature.children:
        if child.kind == document.D_MECHANIC:
            yield html.div(render_mechanic(doc, child))

        elif child.kind == document.D_COST:
            yield html.div(
                html.style_attr('font-size: 10pt;'),

                html.span(
                    # Make sure the text is bold
                    html.style_attr('font-weight: bold;'),

                    'Aspect Point {}: '.format(
                        'Cost' if int(child.content) >= 0 else 'Return')
                ),

                html.span(child.content))

        else:
            yield html.p(
                html.style_attr('font-size: 10pt;'),
                format_content(child.content))


def render_effect(doc, effect):
    yield html.div(
        html.id_attr(effect.id),
        html.h4(format_name(effect.content)))

    for child in effect.children:
        if child.kind == document.D_MECHANIC:
            yield html.div(
                # Make sure the text is bold
                html.style_attr('font-weight: bold; font-size: 10pt;'),

                'Effect Mechanic: ', child.content
            )

        elif child.kind == document.D_COST:
            yield html.div(
                # Make sure the text is bold
                html.style_attr('font-weight: bold; font-size: 10pt;'),

                html.span(
                    'AP Cost: ', child.content
                )
            )

        else:
            yield html.p(
                html.style_attr('font-size: 10pt;'),
                format_content(child.content)
            )


def render_aspect(doc, aspect):
    yield html.div(
        html.id_attr(aspect.id),
        html.h4(format_name(aspect.content)))

    # Figure out some important stuff
    ap_cost = 0

    for grant in aspect.find(document.D_GRANTS):
        cost = grant_cost(doc, grant)
        ap_cost += cost

    yield html.div(
        html.style_attr('font-size: 10pt;'),

        html.span(
            # Make sure the text is bold
            html.style_attr('font-weight: bold;'),

            'Aspect Point {}: '.format(
                'Cost' if ap_cost >= 0 else 'Return')
        ),

        html.span(ap_cost))

    for child in aspect.children:
        if child.kind == document.D_GRANTS:
            yield render_grant(doc, child)
        elif child.kind == document.D_REQUIRES:
            yield render_requires(doc, child)
        else:
            yield html.p(
                html.style_attr('font-size: 10pt;'),
                format_content(child.content)
            )


def render_requires(doc, reqires):
    ref_id, kind, reqires_title = parse_grant(doc, reqires)

    return html.div(
        html.style_attr('font-size: 10pt; padding-top: 5px;'),

        html.span(
            # Make sure the text is bold
            html.style_attr('font-weight: bold;'),

            'Requires {}: '.format(kind.title())
        ),

        html.span(
            html.a(
                html.attribute('href', '#{}'.format(ref_id)),
                ''.join(reqires_title))))


_REPLACEMENT_PATTERN = '<>'
_SUBTYPE_REPLACEMENT_PATTERN = '(<>)'


def format_name(name, subtype=None):
    if subtype is not None:
        return name.replace(_REPLACEMENT_PATTERN, subtype)

    return name


def parse_grant(doc, grant):
    kind, name, subtype, multiplier = parse_grant_spec(grant.content)

    for ref in document.find(doc.root, kind):
        ref_name, ref_subtype = parse_name(ref.content)

        if ref_name != name:
            continue

        # If the ref_subtype is null then we simply ignore it
        if ref_subtype == _REPLACEMENT_PATTERN:
            ref_subtype = subtype

        grant_title = [format_name(ref.content, ref_subtype)]

        if multiplier > 1:
            grant_title.append(' x {}'.format(multiplier))

        return (ref.id, kind, ''.join(grant_title))

    raise ToolError('Unable to locate ref: {}'.format(kind))


def render_grant(doc, grant):
    ref_id, kind, grant_title = parse_grant(doc, grant)

    return html.div(
        html.style_attr('font-size: 10pt; padding-top: 5px;'),

        html.span(
            # Make sure the text is bold
            html.style_attr('font-weight: bold;'),

            'Grants {}: '.format(kind.title())
        ),

        html.span(
            html.a(
                html.attribute('href', '#{}'.format(ref_id)),
                ''.join(grant_title))))


def parse_name(name):
    # Deconstruct the name
    match = _NAME_REGEX.match(name)

    if match is None:
        raise ToolError('Unable to parse name: {}'.format(name))

    # Bind all of the good bits to names
    clean_name = match.group(1).strip()
    subtype = match.group(2)

    return (clean_name, subtype)


def parse_grant_spec(content):
    # Deconstruct the grant
    match = _GRANT_REGEX.match(content)

    if match is None:
        raise ToolError('Unable to parse grant statement: {}'.format(content))

    # Bind all of the good bits to names
    kind = match.group(1).strip()
    name = match.group(2).strip()
    subtype = match.group(3)
    multiplier = match.group(4)

    # Set a sane default for multipliers incase they don't provide one
    multiplier = int(multiplier) if multiplier is not None else 1

    return (kind, name, subtype, multiplier)


def grant_cost(doc, grant):
    ap_cost = 0
    kind, name, subtype, multiplier = parse_grant_spec(grant.content)

    for ref in document.find(doc.root, kind):
        ref_name, ref_subtype = parse_name(ref.content)

        if ref_name != name:
            continue

        if kind == document.D_ABILITY:
            ap_cost += ability_cost(doc, ref)
        else:
            for ref_cost in ref.find(document.D_COST):
                ap_cost += int(ref_cost.content) * multiplier

    return ap_cost


def ability_cost(doc, ability):
    ap_cost = 0

    for difficulty in ability.find(document.D_DIFFICULTY):
        # Check to see if the base difficulty modifies the AP cost
        cost_magnitude = int(difficulty.content) - 15
        ap_cost += -(cost_magnitude / 5)

    for grant in ability.find(document.D_GRANTS):
        ap_cost += grant_cost(doc, grant)

    return ap_cost


def render_ability(doc, ability):
    yield html.div(
        html.id_attr(ability.id),
        html.h4(format_name(ability.content)))

    # Figure out some important stuff
    ap_cost = ability_cost(doc, ability)

    yield html.div(
        html.style_attr('font-size: 10pt;'),

        html.span(
            # Make sure the text is bold
            html.style_attr('font-weight: bold;'),

            'Aspect Point {}: '.format(
                'Cost' if ap_cost >= 0 else 'Return')
        ),

        html.span(ap_cost))

    for child in ability.children:
        if child.kind == document.D_GRANTS:
            yield render_grant(doc, child)
        elif child.kind == document.D_DIFFICULTY:
            yield html.div(
                html.style_attr('font-size: 10pt;'),

                html.span(
                    # Make sure the text is bold
                    html.style_attr('font-weight: bold;'),

                    'Difficulty: '
                ),

                html.span(child.content))
        else:
            yield html.p(
                html.style_attr('font-size: 10pt;'),
                format_content(child.content)
            )


def render_section(doc, section):
    yield html.h3(section.content)

    for child in section.children:
        if child.kind in [document.D_FEATURE, document.D_EFFECT, document.D_ABILITY, document.D_ASPECT]:
            render_func = globals()['render_{}'.format(child.kind)]
            yield html.div(render_func(doc, child))

        else:
            yield html.p(
                html.style_attr('font-size: 10pt;'),
                format_content(child.content)
            )


def render_doc(doc):
    yield html.style_attr('max-width: 1000px; margin-left: 50px;')
    yield html.div(
        html.style_attr('margin-left: 25px;'),
        html.h1(doc.title)
    )

    for section in doc.sections:
        yield render_section(doc, section)


def export_tool(args):
    # Read the configuration or attempt to
    cfg = config.read_config()

    # Read the document
    doc = document.read(cfg.document_file)

    if args.format == 'html':
        with open('{}.html'.format(doc.title), 'w') as html_out:
            html_stmt= html.div(render_doc(doc))

            html_out.write(html_stmt())
    else:
        raise ToolError('No export format {} available.'.format(args.format))


def _matches_spec(node, node_spec, case_insensitive):
    content = node.content or ''
    formatted = content if not case_insensitive else content.lower()

    return fnmatch.fnmatchcase(formatted, node_spec)


def find_tool(args):
    # Read the configuration or attempt to
    cfg = config.read_config()

    # Read the document
    doc = document.read(cfg.document_file)

    # Normalize the matcher
    kind_spec = args.kind.lower()

    # Select nodes that only match our spec
    nodes = [n for n in document.find(doc.root, kind_spec)]

    # Did we find any nodes?
    found_matching_nodes = len(nodes) > 0

    if found_matching_nodes:
        output.console('\n\n\n'.join([str(n) for n in nodes]))
    else:
        raise ToolError(
            'Spec "{}" not found.'.format(args.node_spec),
            error.NODE_NOT_FOUND)


def status_tool(args):
    # Read the configuration or attempt to
    cfg = config.read_config()

    # Read the document
    doc = document.read(cfg.document_file)

    output.console('Document is valid!')
    output.console('Document title: {}'.format(doc.title))
    output.console('Document length: {} nodes'.format(len(doc)))


def add_tool(args):
    # Read the configuration or attempt to
    cfg = config.read_config()

    editor_file_tuple = tempfile.mkstemp()
    edit_document(editor_file_tuple[1], cfg.document_file)


def stash_tool(args):
    if args.stash_tool_name == 'pop':
        stash_tool_pop(args)


def stash_tool_pop(args):
    # Get the stashed doc, if any
    stashed_doc = config.stash_pop()

    if stashed_doc is not None:
        # Read the configuration or attempt to
        cfg = config.read_config()

        try:
            # Edit the file
            edit_document(stashed_doc, cfg.document_file)
        finally:
            # No matter what happens, blast the doc
            os.remove(stashed_doc)
    else:
        output.console('Stash is empty.')


def edit_document(new_doc_file, origin_doc_file):
    editor_cmd = os.getenv(_EDITOR_ENV_KEY, None)

    if editor_cmd is not None:
        _edit_document(editor_cmd, new_doc_file, origin_doc_file)
    else:
        output.console('No editor set. Please set $EDITOR to your prefered editor.')


def _edit_document(editor_cmd, new_doc_file, origin_doc_file):
    continue_editing = True
    while continue_editing is True:
        editor_retval = subprocess.call([editor_cmd, new_doc_file])

        if editor_retval != 0:
            output.console('Editor failed with a non-zero return value. Bailing.')
            break

        try:
            doc = document.read(new_doc_file)
        except Exception as ex:
            output.console(ex)
            doc = None

        # Do we want to merge or stash the new doc?
        stash_document = False
        merge_document = False

        # Keep bugging the user for input until they decide wtf to do
        while continue_editing and not merge_document and not stash_document:
            if doc is not None:
                output.console('Document is valid!')
                output.console('Document length: {} nodes'.format(len(doc)))
                output.console('Stash (s), Merge (m), Abandon (a), or Edit (e)?')

                answer = user_input()

                if answer == 'A' or answer == 'a':
                    continue_editing = False
                elif answer == 'S' or answer == 's':
                    stash_document = True
                elif answer == 'M' or answer == 'm':
                    merge_document = True
                elif answer == 'E' or answer == 'e':
                    break
            else:
                output.console('Document is not valid!\n')
                output.console('Stash (s), Abandon (a), or Edit (e)?')

                answer = user_input()

                if answer == 'A' or answer == 'a':
                    continue_editing = False
                elif answer == 'S' or answer == 's':
                    stash_document = True
                elif answer == 'E' or answer == 'e':
                    break

        if stash_document is True:
            stash_id = config.stash_push(new_doc_file)
            output.console('Stashed: {}'.format(stash_id))

            continue_editing = False
        elif merge_document is True:
            origin_doc = document.read(origin_doc_file)

            if origin_doc is not None:
                doc_idx = select_section(origin_doc)
                updated_doc = document.insert(doc, origin_doc, doc_idx)
                document.write(updated_doc, origin_doc_file)

            continue_editing = False


def select_section(doc):
    options = dict()

    idx = 1
    for doc_idx, section in document.section_nodes(doc):
        options[str(idx)] = (doc_idx, section.arguments)
        idx += 1

    options[str(idx)] = (len(doc), 'Append to End of Document')

    return user_selection(options)


def user_selection(options):
    while True:
        for key in sorted(options):
            _, arguments = options[key]
            output.console('[{}] {}'.format(key, arguments))

        answer = user_input()

        if answer in options:
            doc_idx, _ = options[answer]
            return doc_idx
