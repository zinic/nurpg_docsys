import nurpg.html as html
import nurpg.error as error
import nurpg.config as config
import nurpg.output as output
import nurpg.document as document

import nurpg.tools.export as export


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


def tool_functions():
    return  {
        'init': init_tool,
        'export': export_tool,
        'status': status_tool,
        'find': find_tool
    }


def init_tool(args):
    output.console('Writing document confniguration.')

    try:
        # Attempt to initialize a new configuration
        config.init_config(args.document)

        # If we get here we're a-okay
        output.console('Initialization OK.')
    except Exception as ex:
        ToolError.wrap(ex)


def export_tool(args):
    # Read the configuration or attempt to
    cfg = config.read_config()

    # Read the document
    doc = document.read(cfg.document_file)

    if args.format == 'html':
        with open('{}.html'.format(doc.title), 'w') as html_out:
            html_stmt= html.html(
                html.head(
                    html.title(doc.title)
                ),

                html.body(
                    html.div(export.render_doc(doc))))

            html_out.write(html_stmt())
    else:
        raise ToolError('No export format {} available.'.format(args.format))


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
        output.console(''.join([str(n) for n in nodes]))
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
