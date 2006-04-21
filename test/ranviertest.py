#!/usr/bin/env python
# This file is part of the Ranvier package.
# See http://furius.ca/ranvier/ for license and details.

"""
Simple automated tests, based on the demoapp resource tree for the most part.
"""

# stdlib imports
import sys, os
from os.path import *
# Allow import demoapp.
sys.path.append(join(dirname(dirname(abspath(__file__))), 'demo')) 

# ranvier imports
from ranvier import *

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
        self.assertEquals(mapurl('@@DemoFolderWithMenu'), '/fold')

    def test_backmaps( self ):
        "Testing backmapping URLs."
        # Create a resource tree.
        mapper, root = demoapp.create_application()
        return self._test_backmaps(mapper)
    
    def test_render_reload( self ):
        "Testing reloading the mapper from a rendered rendition."

        # Render the mapper to a set of lines
        mapper, root = demoapp.create_application()
        lines = mapper.render()
        rendered = os.linesep.join(lines)

        # Reload the mapper from these lines.
        loaded_mapper = UrlMapper.load(lines)
        self._test_backmaps(loaded_mapper)

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
def suite():
    suite = unittest.TestSuite()
    suite.addTest(TestMappings("test_backmaps"))
    suite.addTest(TestMappings("test_render_reload"))
    suite.addTest(TestMappings("test_static"))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')

