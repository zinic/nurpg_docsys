import re
import fnmatch

import nurpg.html as html
import nurpg.document as document


# Name specifier regex
_NAME_REGEX = re.compile('^([^\($]+)(?:\(([^\)]+)\))?$')

# Regex for parsing grant statements
_GRANT_REGEX = re.compile('^([^\s]+)\s([^,(]+)(?:\(([^)]+)\))?(?:\,\s?(\d+))?$')

# HTML related formatting items
_CSS_TOP_GAP = html.style_attr('padding-top: 15px;')
_CSS_TOP_GAP_SMALL = html.style_attr('padding-top: 5px;')
_CSS_BOLD = html.style_attr('font-weight: bold;')
_HTML_BR = html.br()()

# Spec components
_REPLACEMENT_PATTERN = '<>'
_SUBTYPE_REPLACEMENT_PATTERN = '(<>)'


###
# Formatters
###

def format_content(content):
    return content.replace('\n\n', _HTML_BR).replace('\n', _HTML_BR)


def format_name(name, subtype=None):
    if subtype is not None:
        return name.replace(_REPLACEMENT_PATTERN, subtype)

    return name


###
# Parsing Functions
##

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


###
# Render Functions
###

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
        html.style_attr('margin-left: 25px; padding-bottom: 5px;'),
        html.h1(doc.title)
    )

    for section in doc.sections:
        yield render_section(doc, section)
