#!/usr/bin/env python
# This file is part of the Ranvier package.
# See http://furius.ca/ranvier/ for license and details.

"""
Simple automated tests, based on the demoapp resource tree for the most part.
"""

# stdlib imports
import sys, os, unittest
from os.path import *
# Allow import demoapp.
sys.path.append(join(dirname(dirname(abspath(__file__))), 'demo'))

# ranvier imports
from ranvier import *
import ranvier.mapper

# ranvier demo imports
import demoapp


#-------------------------------------------------------------------------------
#
class TestMappings(unittest.TestCase):
    """
    Tests backward mapping of URLs.
    """
    def _test_backmaps( self, mapper ):
        "General backmapping tests.."
        mapurl = mapper.mapurl

        self.assertEquals(mapurl('@@Home'), '/home')
        self.assertRaises(RanvierError, mapurl, '@@Home', 'extraparam')
        self.assertEquals(mapurl('@@DemoPrettyEnumResource'), '/prettyres')
        self.assertEquals(mapurl('@@EnumResource'), '/resources')
        self.assertEquals(mapurl('@@ImSpecial'), '/altit')
        self.assertEquals(mapurl('@@AnswerBabbler'), '/deleg')
        self.assertEquals(mapurl('@@PrintUsername', username='martin'),
                          '/users/martin/username')
        self.assertEquals(mapurl('@@PrintName', 'martin'),
                          '/users/martin/name')
        self.assertEquals(mapurl('@@RedirectTest'), '/redirtest')
        self.assertEquals(mapurl('@@LeafPlusOneComponent', comp='president'),
                          '/lcomp/president')
        self.assertRaises(RanvierError, mapurl,
                          '@@LeafPlusOneComponent', 'george', comp='junior')
        self.assertEquals(mapurl('@@DemoFolderWithMenu'), '/fold/')

    def test_backmaps( self ):
        "Testing backmapping URLs."
        # Create a resource tree.
        mapper = UrlMapper()
        root = demoapp.create_application(mapper)
        return self._test_backmaps(mapper)

    def test_render_reload( self ):
        "Testing reloading the mapper from a rendered rendition."

        # Render the mapper to a set of lines
        mapper = UrlMapper()
        root = demoapp.create_application(mapper)
        lines = mapper.render()
        rendered = os.linesep.join(lines)

        # Reload the mapper from these lines.
        loaded_mapper = UrlMapper.load(lines)
        self._test_backmaps(loaded_mapper)

        # Round-trip: render and compare to the original file.
        loaded_lines = loaded_mapper.render()
        self.assertEquals(loaded_lines, lines)

        # Load from a file.
        fromfile_mapper = UrlMapper.urlload('example-resources.txt')

    def test_static( self ):
        self._test_static(None)
        self._test_static('/root')

    def _test_static( self, rootloc ):
        "Testing static resources."

        # Get some mapper.
        mapper = UrlMapper(rootloc=rootloc)

        # Test valid cases.
        mapper.add_static('@@Static1', '/home')
        self.assertEquals(mapper.mapurl('@@Static1'), '/home')

        mapper.add_static('@@Relative1', 'home')
        self.assertEquals(mapper.mapurl('@@Relative1'),
                          '%s/home' % (rootloc or ''))

        mapper.add_static('@@Static2', '/documents/legal')
        self.assertEquals(mapper.mapurl('@@Static2'), '/documents/legal')

        mapper.add_static('@@Static3', '/documents/faq/questions')
        mapper.add_static('@@Static4', '/users/(user)')
        mapper.add_static('@@Static5', '/users/(user)/home')
        self.assertEquals(mapper.mapurl('@@Static5', 'blais'),
                          '/users/blais/home')

        mapper.add_static('@@Static6', '/users/(user)/home', {'user': 'blais'})
        mapper.add_static('@@Static7', '/users/(user)/(address)')
        mapper.add_static('@@Static8', 'http://aluya.ca/u/(user)/home')
        self.assertEquals(mapper.mapurl('@@Static8', 'blais'),
                          'http://aluya.ca/u/blais/home')

        # static with formatting
        mapper.add_static('@@Static9', 'http://aluya.ca/r/(rid%04d)/home')
        self.assertEquals(mapper.mapurl('@@Static9', 317),
                          'http://aluya.ca/r/0317/home')

        mapper.add_static('@@Missing1', '/users/(user)/home')
        self.assertRaises(RanvierError, mapper.mapurl, '@@Missing1')

        mapper.add_static('@@Default1', '/users/(user)/home', {'user': 'blais'})
        self.assertEquals(mapper.mapurl('@@Default1'), '/users/blais/home')

        mapper.add_static('@@Context1', '/users/(user)/home')
        class Dummy: pass
        o = Dummy()
        o.user = 'blais'
        self.assertEquals(mapper.mapurl('@@Context1', o), '/users/blais/home')
        o = {'user': 'blais'}
        self.assertEquals(mapper.mapurl('@@Context1', o), '/users/blais/home')

        # (Test override by kwd arg of value present in object/dict.)
        self.assertEquals(mapper.mapurl('@@Context1', o, user='rachel'),
                          '/users/rachel/home')

        # Test error cases.
        self.assertRaises(RanvierError, mapper.mapurl, '@@Missing1')
        self.assertRaises(RanvierError, mapper.add_static,
                          '@@Static1', '/duplicate')

        self.assertRaises(RanvierError, mapper.add_static,
                          '@@ExtraneousDef1', '/home', {'somevar': 'bli'})

        self.assertRaises(RanvierError, mapper.add_static,
                          '@@ExtraneousDef2', '/users/(user)', {'user': 'blais',
                                                                'other': 'bli'})
        self.assertRaises(RanvierError, mapper.add_static,
                          '@@InvalidPattern1', '/users/(user)bli')

        self.assertRaises(RanvierError, mapper.add_static,
                          '@@InvalidPattern2', '/users/bli(user)/home')

        self.assertRaises(RanvierError, mapper.add_static,
                          '@@Collision', '/users/(user)/document/(user)/home', )

        self.assertRaises(RanvierError, mapper.mapurl,
                          '@@Context1', o, 'posarg')


#-------------------------------------------------------------------------------
#
class TestConversions(unittest.TestCase):
    """
    Tests string/pattern conversions.
    """
    def test_urlpattern( self ):
        "Test conversions from/to URL patterns."
        fun = ranvier.mapper.urlpattern_to_components

        # All fixed.
        self.assertEquals(
            fun('/documents/faq/part1'), 
            (('', '', True, [('documents', False, None, None),
                             ('faq', False, None, None),
                             ('part1', False, None, None)], '', ''), False) )
        
        # Non-terminal
        self.assertEquals(
            fun('/documents/faq/'), 
            (('', '', True, [('documents', False, None, None),
                             ('faq', False, None, None),], '', ''), True) )

        # With one variable.
        self.assertEquals(
            fun('/users/(username)/profile'), 
            (('', '', True, [('users', False, None, None),
                             ('username', True, None, None),
                             ('profile', False, None, None)], '', ''), False) )

        # Variable with default
        self.assertEquals(
            fun('/users/(username)/profile', {'username': 'martin'}), 
            (('', '', True, [('users', False, None, None),
                                ('username', True, 'martin', None),
                                ('profile', False, None, None)], '', ''), False) )

        # Variable with formatting
        self.assertEquals(
            fun('/users/(userid%08d)/profile'), 
            (('', '', True, [('users', False, None, None),
                                ('userid', True, None, '08d'),
                                ('profile', False, None, None)], '', ''), False) )

        # Test with multiple components
        self.assertEquals(
            fun('/users/(username)/trip/(id)/view'), 
            (('', '', True, [('users', False, None, None),
                                ('username', True, None, None),
                                ('trip', False, None, None),
                                ('id', True, None, None),
                                ('view', False, None, None)], '', ''), False) )

        # Test with many components, defaults and formatting.
        self.assertEquals(
            fun('/users/(username)/trip/(id%08d)/view', {'id': 4}), 
            (('', '', True, [('users', False, None, None),
                                ('username', True, None, None),
                                ('trip', False, None, None),
                                ('id', True, 4, '08d'),
                                ('view', False, None, None)], '', ''), False) )

        # All fixed, external.
        fun('http://domain.com/users')

        # With variables, external.
        fun('http://domain.com/users/(username)/view')

        # Relative.
        self.assertEquals(
            fun('users/(username)/profile'), 
            (('', '', False, [('users', False, None, None),
                                 ('username', True, None, None),
                                 ('profile', False, None, None)], '', ''), False) )

        # Test with invalid defaults.
        assertRaises(RanvierError, fun,
                     '/users/(username)/profile', {'userid': 17})


    def test_template( self ):
        "Test conversion to string template."

        mapper = UrlMapper(rootloc='/demo')
        root = demoapp.create_application(mapper)
        mapurl, mapurl_pattern = mapper.mapurl, mapper.mapurl_pattern

        tests = (
            ('@@ExternalExample', (),
             'http://paulgraham.com/', 'http://paulgraham.com/'),
            ('@@Root', (),
             '/demo/', '/demo/'),
            ('@@ImSpecial', (),
             '/demo/altit', '/demo/altit'),
            ('@@Atocha', (),
             '/atocha/index.html', '/atocha/index.html'),
            ('@@AnswerBabbler', (),
             '/demo/deleg', '/demo/deleg'),
            ('@@DemoFolderWithMenu', (),
             '/demo/fold/', '/demo/fold/'),
            ('@@SimpleGreed', (),
             '/demo/fold/greed', '/demo/fold/greed'),
            ('@@SimpleHamming', (),
             '/demo/fold/ham', '/demo/fold/ham'),
            ('@@SimpleThought', (),
             '/demo/fold/think', '/demo/fold/think'),
            ('@@IntegerComponent', (1042,),
             '/demo/formatted/00001042',
             '/demo/formatted/(uid%08d)'),
            ('@@Home', (),
             '/demo/home', '/demo/home'),
            ('@@InternalRedirectTest', (),
             '/demo/internalredir', '/demo/internalredir'),
            ('@@LeafPlusOneComponent', ('bli',),
             '/demo/lcomp/bli', '/demo/lcomp/(comp)'),
            ('@@DemoPrettyEnumResource', (),
             '/demo/prettyres', '/demo/prettyres'),
            ('@@RedirectTest', (),
             '/demo/redirtest', '/demo/redirtest'),
            ('@@EnumResource', (),
             '/demo/resources', '/demo/resources'),
            ('@@Stylesheet', (),
             '/demo/style.css', '/demo/style.css'),
            ('@@UserData', ('rachel', 'school'),
             '/demo/users/rachel/data/school',
             '/demo/users/(username)/data/(userdata)'),
            ('@@PrintName', ('rachel',),
             '/demo/users/rachel/name',
             '/demo/users/(username)/name'),
            ('@@PrintUsername', ('rachel',),
             '/demo/users/rachel/username',
             '/demo/users/(username)/username'),
            )

        for resid, args, rendered, pattern in tests:
            assertEquals(mapurl(resid, *args), rendered)
            assertEquals(mapurl_pattern(resid), pattern)

    def test_match( self ):
        "Test matching known URLs."

        mapper = UrlMapper(rootloc='/demo')
        root = demoapp.create_application(mapper)
        match = mapper.match

        tests = (
            ('@@ImSpecial', '/demo/altit', {}),
            ('@@SimpleThought', '/demo/fold/think', {}),
            ('@@IntegerComponent', '/demo/formatted/00001042', {'uid': 1042}),
            ('@@LeafPlusOneComponent', '/demo/lcomp/bli', {'comp': 'bli'}),
            ('@@UserData', '/demo/users/rachel/data/school',
             {'username': 'rachel', 'userdata': 'school'}),
            ('@@LeafPlusOneComponent', 'http://furius.ca/demo/lcomp/bli',
             {'comp': 'bli'}),
            )

        for resid, url, expected in tests:
            assertEquals(match(resid, url), expected)


#-------------------------------------------------------------------------------
#
def assertRaises(excClass, callableObj, *args, **kwargs):
    try:
        callableObj(*args, **kwargs)
    except excClass:
        return
    else:
        if hasattr(excClass,'__name__'): excName = excClass.__name__
        else: excName = str(excClass)
        raise self.failureException, "%s not raised" % excName

def assertEquals( first, second ):
    if not first == second:
        raise RuntimeError('%r != %r' % (first, second))


#-------------------------------------------------------------------------------
#
def suite():
    suite = unittest.TestSuite()
    suite.addTest(TestMappings("test_backmaps"))
    suite.addTest(TestMappings("test_render_reload"))
    suite.addTest(TestMappings("test_static"))
    suite.addTest(TestConversions("test_urlpattern"))
    suite.addTest(TestConversions("test_template"))
    suite.addTest(TestConversions("test_match"))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')

