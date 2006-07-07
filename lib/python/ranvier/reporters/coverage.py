#!/usr/bin/env python
# This file is part of the Ranvier package.
# See http://furius.ca/ranvier/ for license and details.

"""
Call graph reporter.

This is an object that can be used for the code that reports the call graph.  To
be used only for debugging.
"""

# stdlib imports
import anydbm, StringIO, re

# ranvier imports
from ranvier import RanvierError
from ranvier.reporters.reporter import SimpleReporter
from ranvier.miscres import LeafResource
import ranvier.template


__all__ = ('coverage_render_html_table', 'coverage_render_cmdline',
           'create_coverage_reporter',
           'ReportCoverage', 'ResetCoverage',
           'DbmCoverageReporter', 'SqlCoverageReporter')


#-------------------------------------------------------------------------------
#
def coverage_output_generator(mapper, coverage,
                              ids_ignore_handle, ids_ignore_render):
    """
    Generator that drives the output of the coverage results.
    """
    sortkey = lambda x: x.resid
    mappings = sorted(mapper.itervalues(), key=sortkey)

    set_ignore_handle = frozenset(ids_ignore_handle)
    set_ignore_render = frozenset(ids_ignore_render)

    for mapping in mappings:

        # Get the coverage information.
        hcount, rcount = coverage.get(mapping.resid, (0, 0))

        # Render a row.
        tip = mapper.mapurl_pattern(mapping.resid)

        # Render 'handled' count.
        if mapping.resid in set_ignore_handle:
            hstate = 'ignore'

        elif hcount == 0:
            hstate = 'fail'

        else:
            hstate = 'success'

        # Render 'rendered' count.
        if mapping.resid in set_ignore_render:
            rstate = 'ignore'

        elif rcount == 0:
            rstate = 'fail'
        else:
            rstate = 'success'

        yield mapping.resid, tip, (hcount, hstate), (rcount, rstate)


#-------------------------------------------------------------------------------
#
def coverage_render_html_table(mapper, coverage,
                               ids_ignore_handle, ids_ignore_render):
    """
    Render an HTML table of the coverage results.

    'mapper' is the mapper object that we use for building the list.

    'coverage' is the coverage information, a dict mapping a resource-id to a
    tuple of counts.

    'ids_hide', 'ids_ignore_handle', 'ids_ignore_render': lists of resource-ids
    that should be hidden or ignored (grayed out).
    """
    oss = StringIO.StringIO()
    oss.write('<table id="coverage-report">\n')
    oss.write(' <thead><tr>'
              '<td>Resource</td>'
              '<td>Handled</td>'
              '<td>Rendered</td>'
              '</tr></thead>\n')
    
    for resid, tip, (hcount, hstate), (rcount, rstate) in \
            coverage_output_generator(mapper, coverage,
                                      ids_ignore_handle, ids_ignore_render):
        
        # Render a row.
        oss.write('  <tr>\n    <td class="cov-resid">'
                  '<acronym title="%s">%s</acronym></td>\n' %
                  (tip, resid))
        oss.write('    <td class="cov-%s">%s</td>\n' % (hstate, hcount))
        oss.write('    <td class="cov-%s">%s</td>\n' % (rstate, rcount))
        oss.write('  </tr>\n')

    oss.write('</table>\n')
    return oss.getvalue()

# CSS to be included for rendering the HTML table nicely, with colors.
coverage_css = '''

table#coverage-report {
  border-collapse: collapse;
}

table#coverage-report td {
  padding-left: 2em;
  padding-right: 2em;
  border: thin solid black;
}

table#coverage-report td.cov-resid {
  font-family: monospace;
  font-size: larger;
}

table#coverage-report td.cov-fail {
  background-color: #F66;
}

table#coverage-report td.cov-success {
  background-color: #6F6;
}

table#coverage-report td.cov-ignore {
  background-color: #DDD;
}

table#coverage-report thead {
  background-color: #EEE;
  border-bottom: medium solid black;
}

'''

#-------------------------------------------------------------------------------
#
def coverage_render_cmdline(mapper, coverage,
                            ids_ignore_handle, ids_ignore_render):
    """
    Render the coverage results as they should appear on the output of a
    command-line.  See coverage_render_html_table() for details about the input
    parameters.

    This returns two strings: normal output and errors.
    """
    output, errors = StringIO.StringIO(), StringIO.StringIO()

    maxlen = max(len(x.resid) for x in mapper.itervalues())
    head = '%%-%ds   %%8s   %%8s\n' % maxlen
    output.write(head % ('Resource-Id', 'Handled', 'Rendered'))
    output.write(head % ('-' * maxlen, '-' * 8, '-' * 8))

    herrors, rerrors = 0, 0
    fmt = '%%-%ds   %%8d   %%8d  %%s\n' % maxlen
    for resid, tip, (hcount, hstate), (rcount, rstate) in \
            coverage_output_generator(mapper, coverage,
                                      ids_ignore_handle, ids_ignore_render):

        marker = ''
        if rstate == 'fail':
            errors.write("Warning: '%s' not rendered.\n" % resid)
            marker = 'WARNING'
            rerrors += 1

        if hstate == 'fail':
            errors.write("Error: '%s' not handled.\n" % resid)
            marker = 'ERROR'
            herrors += 1

        output.write(fmt % (resid, hcount, rcount, marker))

    return output.getvalue(), errors.getvalue(), herrors, rerrors


#-------------------------------------------------------------------------------
#
class ReportCoverage(LeafResource):
    """
    Outputs a nice HTML table of the saved resource coverage.
    """
    def __init__(self, mapper, reader_fun,
                 ids_ignore_handle=None, ids_ignore_render=None,
                 **kwds):
        """
        'reader_fun' is a function that can be invoked to obtain a dict of
        resource-id's to pairs of (handled-count, rendered-count).

        'mapper' is the URL mapper.  We need it in order to be able to list
        resources that have not been rendered at all.
        """
        LeafResource.__init__(self, **kwds)

        self.mapper = mapper

        assert reader_fun is not None
        self.reader_fun = reader_fun

        self.ignore_handle = tuple(ids_ignore_handle) or ()
        self.ignore_render = tuple(ids_ignore_render) or ()

    def get_html_table(self):
        """
        Return an HTML table with the coverage results.
        """
        # Extract the coverage.
        coverage = self.reader_fun()

        # Automatically add the absolute ids to be ignored.
        absids = tuple(self.mapper.getabsoluteids())

        return coverage_render_html_table(self.mapper, coverage,
                                          self.ignore_handle + absids,
                                          self.ignore_render)

    def handle(self, ctxt):
        ctxt.response.setContentType('text/html')
        ranvier.template.render_header(
            ctxt.response, 'Resource Coverage Results', coverage_css)
        ctxt.response.write(self.get_html_table())
        ranvier.template.render_footer(ctxt.response)


class ResetCoverage(LeafResource):
    """
    Reset the coverage analyser.
    """
    def __init__(self, reset_fun, **kwds):
        """
        'reset_fun' is a function to reset the coverage analyser.
        """
        LeafResource.__init__(self, **kwds)
        self.reset_fun = reset_fun

    def handle(self, ctxt):
        # Start the coverage analyser
        self.reset_fun()

        ctxt.response.setContentType('text/plain')
        ctxt.response.write('OK coverage reset')


#-------------------------------------------------------------------------------
#
class DbmCoverageReporter(SimpleReporter):
    """
    Concrete implementation that stores the mappings in a dbm databases.
    """
    def __init__(self, dbmfn, read_only=None):
        SimpleReporter.__init__(self)

        self.fn = dbmfn
        self.dbmfn = dbmfn

        # Open the database file.
        self.dbm = anydbm.open(dbmfn, read_only and 'r' or 'c')

    def __del__(self):
        self.dbm.close()

    def reset(self):
        self.dbm.close()
        self.dbm = anydbm.open(self.dbmfn, 'n')

    def read_entry(self, resid):
        try:
            hcount, rcount = map(int, self.dbm[resid].split())
        except KeyError:
            hcount, rcount = 0, 0
        return hcount, rcount

    def write_entry(self, resid, hcount, rcount):
        self.dbm[resid] = '%d %d' % (hcount, rcount)

    def end(self):
        if self.last_handled:
            hcount, rcount = self.read_entry(self.last_handled)
            hcount += 1
            self.write_entry(self.last_handled, hcount, rcount)

        for resid in self.rendered_list:
            hcount, rcount = self.read_entry(resid)
            rcount += 1
            self.write_entry(resid, hcount, rcount)

    def get_coverage(self):
        """
        Read the results for the resource that will render the results.
        """
        allresults = {}
        for resid in self.dbm.keys():
            allresults[resid] = self.read_entry(resid)
        return allresults

#-------------------------------------------------------------------------------
#
class SqlCoverageReporter(SimpleReporter):
    """
    Concrete implementation that stores the mappings in an SQL database, or
    whatever supports the DBAPI-2.0 protocol.
    """
    table_name = 'ranvier_coverage'

    schema = '''

       CREATE TABLE %s (

          -- resource id
          resid   TEXT PRIMARY KEY,

          -- handled count
          hcount  INT,

          -- rendered count
          rcount  INT
       );

    ''' % table_name

    def __init__(self, dbmodule, acquire_conn, release_conn):
        """
        'dbmodule' is expected to be a DBAPI-2.0 implementation.  'acquire_conn'
        and 'release_conn' are callables to acquire and release a connection.
        """
        
        SimpleReporter.__init__(self)

        self.dbmodule = dbmodule
        self.acquire_conn = acquire_conn
        self.release_conn = release_conn

        # Create the table if it does not exist.
        conn = self.acquire_conn()
        try:
            curs = conn.cursor()
            curs.execute("""
              SELECT table_name FROM information_schema.tables
              WHERE table_name = %s
            """, (self.table_name,))
            if curs.rowcount == 0:
                curs.execute(self.schema)
                conn.commit()
        finally:
            self.release_conn(conn)

    def reset(self):
        conn = self.acquire_conn()
        try:
            curs = conn.cursor()

            curs.execute('DROP TABLE %s' % self.table_name)
            curs.execute(self.schema)

        finally:
            self.release_conn(conn)

    def increment_col(self, resid, col, curs):
        """
        Increment a column for a specific resource-id.
        """
        curs.execute('''
          UPDATE %s SET %s = %s + 1 WHERE resid = %%s
        ''' % (self.table_name, col, col), (resid,))

        if curs.rowcount == 0:
            curs.execute('''
              INSERT INTO %s (resid, hcount, rcount)
                VALUES (%%s, %%s, %%s);
            ''' % self.table_name, (resid, 0, 0))
            curs.execute('''
              UPDATE %s SET %s = %s + 1 WHERE resid = %%s
            ''' % (self.table_name, col, col), (resid,))

    def end(self):
        conn = self.acquire_conn()
        try:
            curs = conn.cursor()

            if self.last_handled:
                self.increment_col(self.last_handled, 'hcount', curs)

            for resid in self.rendered_list:
                self.increment_col(resid, 'rcount', curs)

            conn.commit()

        finally:
            self.release_conn(conn)

    def get_coverage(self):
        """
        Read the results for the resource that will render the results.
        """
        conn = self.acquire_conn()
        try:
            curs = conn.cursor()

            curs.execute('''
              SELECT resid, hcount, rcount FROM %s
            ''' % self.table_name)

            allresults = {}
            for resid, hcount, rcount in curs:
                allresults[resid] = (hcount, rcount)

        finally:
            self.release_conn(conn)

        return allresults


#-------------------------------------------------------------------------------
#
# Regexp for connection string, e.g. postgres://user:password@host/dbname
type_re = re.compile('([a-z]+)://(.+)$')
conn_str_re = re.compile(
    '([a-z]+)(?::([^@]+))?@([a-zA-Z0-9]+)/([a-zA-Z0-9_\-]+)')

def create_coverage_reporter(connection_str):
    """
    Create one of the coverage reporters from a connection string.  This is used
    by the command-line module to specify a database connection via a single
    string.
    """
    mo = type_re.match(connection_str)
    if not mo:
        raise RanvierError("Error: Invalid connection string '%s'." %
                           connection_str)
    
    method, conndesc = mo.groups()

    # Support dbm.
    if method == 'dbm':
        # connstr is expected to be the filename.
        reporter = DbmCoverageReporter(conndesc, True)

    # Support SQL databases.
    elif method in ('postgres',):
        try:
            mo = conn_str_re.match(conndesc)
            if not mo:
                raise RanvierError(
                    "Error: Invalid database description '%s'." % conndesc)

            user, passwd, host, dbname = map(lambda x: x or '', mo.groups())

            if method == 'postgres':
                import psycopg2 as dbmodule
                conn = dbmodule.connect(database=dbname,
                                        host=host,
                                        user=user,
                                        password=passwd)

            def acquire():
                return conn # Unique reference to connection.

            def release(conn):
                pass

            reporter = SqlCoverageReporter(dbmodule, acquire, release)

        except Exception, e:
            raise RanvierError(
                "Error: Could not connect to database: '%s'." % e)
    else:
        # Note: I'm sure you could easily add other supported types...  it's
        # pretty much just a matter of establishing a connection.
        raise RanvierError(
            "Error: Method '%s' not supported, invalid method?" % method)

    return reporter

