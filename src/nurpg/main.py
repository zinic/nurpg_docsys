import sys
import logging
import argparse

import nurpg.about as about
import nurpg.error as error
import nurpg.config as config
import nurpg.output as output
import nurpg.document as document

import nurpg.tools.cli as tools

# Logging!
_LOG = logging.getLogger(__name__)


def build_argparser():
    argparser = argparse.ArgumentParser(
        prog='nurpgd',
        description='NuRPG Document Manager')

    argparser.add_argument(
        '-v', '--version',
        action='version',
        version=about.VERSION)

    argparser.add_argument(
        '-D', '--debug',
        dest='wants_debug',
        action='store_true',
        default=False,
        help="""Enables debug output and code paths.""")

    argparser.add_argument(
        '-q', '--quiet',
        dest='wants_quiet',
        action='store_true',
        default=False,
        help="""
            Sets the logging output to quiet. This supercedes enabling the
            debug output switch.""")

    subparsers = argparser.add_subparsers(
        dest='tool_name',
        title='NuRPG Document Commands',
        help='Commands available.')

    # init sub-directive
    init_parser = subparsers.add_parser(
        'init',
        help='Initializes a document context for this directory.')

    init_parser.add_argument(
        'document',
        help='Name of the NuRPG document file.'
    )

    # convert sub-directive
    export_parser= subparsers.add_parser(
        'export',
        help='Initializes a document context for this directory.')

    export_parser.add_argument(
        'format',
        help='Name of the export format.'
    )

    # find sub-directive
    find_parser = subparsers.add_parser(
        'find',
        help='Reads the document file and to allow for lookups to be done '
             'against it.')

    find_parser.add_argument(
        'kind',
        help='The desired document node kind.'
    )

    # status sub-directive
    status_parser= subparsers.add_parser(
        'status',
        help='Reads the document file and checks its vailidity.')

    return argparser


def run():
    # Set a sane retval
    retval = error.GENERAL_FAILURE

    # Argument handling
    argparser = build_argparser()

    if len(sys.argv) <= 1:
        argparser.print_help()
    else:
        # Parse the args and load the config
        args = argparser.parse_args()

        # Set up our logging config first
        if args.wants_debug:
            logging.basicConfig(level=logging.DEBUG)
        else:
            logging.basicConfig(level=logging.WARN)

        try:
            # Run the associated tool function
            tool_func = tools.tool_functions().get(args.tool_name)
            tool_func(args)

            # Looks like everything ran okay
            retval = error.OKAY
        except tools.ToolError as tex:
            output.console(tex.msg)
            retval = tex.errno

            _LOG.exception(tex)
        except error.ErrorMessage as emex:
            output.console(emex.msg)
            retval = error.BAD_DOCUMENT

            _LOG.exception(emex)
        except Exception as ex:
            output.console('Uncaught exception! This should be wrapped as an '
                           'ErrorMessage at the very least.')

            _LOG.exception(ex)

    sys.exit(retval)
