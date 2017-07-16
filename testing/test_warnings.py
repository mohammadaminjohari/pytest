# -*- coding: utf8 -*-
from __future__ import unicode_literals

import sys

import pytest


WARNINGS_SUMMARY_HEADER = 'warnings summary'

@pytest.fixture
def pyfile_with_warnings(testdir, request):
    """
    Create a test file which calls a function in a module which generates warnings.
    """
    testdir.syspathinsert()
    test_name = request.function.__name__
    module_name = test_name.lstrip('test_') + '_module'
    testdir.makepyfile(**{
        module_name: '''
            import warnings
            def foo():
                warnings.warn(UserWarning("user warning"))
                warnings.warn(RuntimeWarning("runtime warning"))
                return 1
        ''',
        test_name: '''
            import {module_name}
            def test_func():
                assert {module_name}.foo() == 1
        '''.format(module_name=module_name)
    })


def test_normal_flow(testdir, pyfile_with_warnings):
    """
    Check that the warnings section is displayed, containing test node ids followed by
    all warnings generated by that test node.
    """
    result = testdir.runpytest()
    result.stdout.fnmatch_lines([
        '*== %s ==*' % WARNINGS_SUMMARY_HEADER,

        '*test_normal_flow.py::test_func',

        '*normal_flow_module.py:3: UserWarning: user warning',
        '*  warnings.warn(UserWarning("user warning"))',

        '*normal_flow_module.py:4: RuntimeWarning: runtime warning',
        '*  warnings.warn(RuntimeWarning("runtime warning"))',
        '* 1 passed, 2 warnings*',
    ])
    assert result.stdout.str().count('test_normal_flow.py::test_func') == 1


def test_setup_teardown_warnings(testdir, pyfile_with_warnings):
    testdir.makepyfile('''
        import warnings
        import pytest

        @pytest.fixture
        def fix():
            warnings.warn(UserWarning("warning during setup"))
            yield
            warnings.warn(UserWarning("warning during teardown"))

        def test_func(fix):
            pass
    ''')
    result = testdir.runpytest()
    result.stdout.fnmatch_lines([
        '*== %s ==*' % WARNINGS_SUMMARY_HEADER,

        '*test_setup_teardown_warnings.py:6: UserWarning: warning during setup',
        '*warnings.warn(UserWarning("warning during setup"))',

        '*test_setup_teardown_warnings.py:8: UserWarning: warning during teardown',
        '*warnings.warn(UserWarning("warning during teardown"))',
        '* 1 passed, 2 warnings*',
    ])


@pytest.mark.parametrize('method', ['cmdline', 'ini'])
def test_as_errors(testdir, pyfile_with_warnings, method):
    args = ('-W', 'error') if method == 'cmdline' else ()
    if method == 'ini':
        testdir.makeini('''
            [pytest]
            filterwarnings= error
            ''')
    result = testdir.runpytest(*args)
    result.stdout.fnmatch_lines([
        'E       UserWarning: user warning',
        'as_errors_module.py:3: UserWarning',
        '* 1 failed in *',
    ])


@pytest.mark.parametrize('method', ['cmdline', 'ini'])
def test_ignore(testdir, pyfile_with_warnings, method):
    args = ('-W', 'ignore') if method == 'cmdline' else ()
    if method == 'ini':
        testdir.makeini('''
        [pytest]
        filterwarnings= ignore
        ''')

    result = testdir.runpytest(*args)
    result.stdout.fnmatch_lines([
        '* 1 passed in *',
    ])
    assert WARNINGS_SUMMARY_HEADER not in result.stdout.str()



@pytest.mark.skipif(sys.version_info < (3, 0),
                    reason='warnings message is unicode is ok in python3')
def test_unicode(testdir, pyfile_with_warnings):
    testdir.makepyfile('''
        # -*- coding: utf8 -*-
        import warnings
        import pytest


        @pytest.fixture
        def fix():
            warnings.warn(u"测试")
            yield

        def test_func(fix):
            pass
    ''')
    result = testdir.runpytest()
    result.stdout.fnmatch_lines([
        '*== %s ==*' % WARNINGS_SUMMARY_HEADER,
        '*test_unicode.py:8: UserWarning: \u6d4b\u8bd5*',
        '* 1 passed, 1 warnings*',
    ])


@pytest.mark.skipif(sys.version_info >= (3, 0),
                    reason='warnings message is broken as it is not str instance')
def test_py2_unicode(testdir, pyfile_with_warnings):
    testdir.makepyfile('''
        # -*- coding: utf8 -*-
        import warnings
        import pytest


        @pytest.fixture
        def fix():
            warnings.warn(u"测试")
            yield

        def test_func(fix):
            pass
    ''')
    result = testdir.runpytest()
    result.stdout.fnmatch_lines([
        '*== %s ==*' % WARNINGS_SUMMARY_HEADER,

        '*test_py2_unicode.py:8: UserWarning: \u6d4b\u8bd5',
        '*warnings.warn(u"\u6d4b\u8bd5")',
        '*warnings.py:*: UnicodeWarning: Warning is using unicode non*',
        '* 1 passed, 2 warnings*',
    ])


def test_works_with_filterwarnings(testdir):
    """Ensure our warnings capture does not mess with pre-installed filters (#2430)."""
    testdir.makepyfile('''
        import warnings

        class MyWarning(Warning):
            pass

        warnings.filterwarnings("error", category=MyWarning)

        class TestWarnings(object):
            def test_my_warning(self):
                try:
                    warnings.warn(MyWarning("warn!"))
                    assert False
                except MyWarning:
                    assert True
    ''')
    result = testdir.runpytest()
    result.stdout.fnmatch_lines([
        '*== 1 passed in *',
    ])
