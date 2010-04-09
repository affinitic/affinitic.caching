# -*- coding: utf-8 -*-
"""
arsia.cerise.core

Licensed under the GPL license, see LICENCE.txt for more details.
Copyright by Affinitic sprl

$Id: event.py 67630 2006-04-27 00:54:03Z jfroche $
"""
import unittest

from zope.testing import doctest

from zope.app.testing.placelesssetup import setUp, tearDown
from zope.configuration.xmlconfig import XMLConfig

optionflags = doctest.REPORT_ONLY_FIRST_FAILURE | doctest.ELLIPSIS

import arsia.cerise.core


class B(object):
    value = None


class User(object):
    pass


def configurationSetUp(test):
    setUp()
    XMLConfig('testing.zcml', arsia.cerise.core)()


def configurationTearDown(test):
    tearDown()

OPTIONFLAGS = (doctest.ELLIPSIS |
               doctest.REPORT_ONLY_FIRST_FAILURE |
               doctest.NORMALIZE_WHITESPACE)


def test_suite():
    tests = (
        doctest.DocFileSuite('memcached.txt',
                             optionflags=OPTIONFLAGS,
                             package="arsia.cerise.core",
                             setUp=configurationSetUp,
                             tearDown=configurationTearDown),
        )
    return unittest.TestSuite(tests)
