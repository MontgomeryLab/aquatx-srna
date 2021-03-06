#!/usr/bin/env python

import os
import shutil
import sys
import time
import unittest

import psutil

import aquatx.aquatx as aquatx
import tests.unit_test_helpers as helpers

"""

Contains tests for aquatx.py, both from direct source-level calls
as well as post-install testing of invocation by terminal. Each
test covers both environments.

"""


class test_aquatx(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        # Change CWD to test folder if test was invoked from project root (ex: by Travis)
        if os.path.basename(os.getcwd()) == 'aquatx-srna':
            os.chdir(f".{os.sep}tests")

        # For pre-install tests
        self.aquatx_cwl_path = '../aquatx/cwl'
        self.aquatx_extras_path = '../aquatx/extras'

        # For post-install tests
        os.system("pip install ../ > /dev/null")

        # For both pre and post install
        self.config_file = './testdata/run_config_template.yml'
        self.expected_cwl_dir_tree = {
            'cwl': {
                'files': set(),
                'tools': {
                    'files': {
                        'aquatx-deseq.cwl', 'bowtie.cwl', 'bowtie2.cwl',
                        'aquatx-collapse.cwl', 'bowtie-build.cwl',
                        'aquatx-count.cwl', 'aquatx-merge.cwl', 'fastp.cwl'
                    }
                },
                'workflows': {
                    'files': {'aquatx_wf.cwl'}
                }
            }
        }

    """
    Testing that get-template copies the correct files 
    to the current directory.
    """

    def test_get_template(self):
        test_functions = [
            helpers.LambdaCapture(lambda: aquatx.get_template(self.aquatx_extras_path)),  # The pre-install invocation
            helpers.ShellCapture("aquatx get-template")                                   # The post-install command
        ]
        template_files = ['run_config_template.yml', 'samples.csv', 'features.csv']

        def dir_entry_ct():
            return len(os.listdir('.'))

        for test_context in test_functions:
            try:
                # Count number of entries in current directory before test
                dir_before_count = dir_entry_ct()
                with test_context as test:
                    test()

                # Check that exactly 3 files were produced by the command
                self.assertEqual(
                    dir_entry_ct() - dir_before_count, 3,
                    f"Abnormal number of template files. Expected 3. Function: {test_context}")

                # Check that each expected file was produced
                for file in template_files:
                    self.assertTrue(os.path.isfile(file),
                                    f"An expected template file wasn't copied: {file}, function: {test_context}")
                    os.remove(file)
            finally:
                # Remove the local template files if necessary, even if an exception was thrown above
                for file in template_files:
                    if os.path.isfile(file): os.remove(file)

    """
    Testing that setup-cwl with a None/none config file 
    copies workflow files without mentioning a config file
    """

    def test_setup_cwl_noconfig(self):
        no_config = ['None', 'none']
        for config in no_config:
            test_functions = [
                helpers.LambdaCapture(lambda: aquatx.setup_cwl(self.aquatx_cwl_path, config)),
                helpers.ShellCapture(f"aquatx setup-cwl --config {config}")
            ]

            for test_context in test_functions:
                try:
                    with test_context as test:
                        test()

                        # Check that the function did not mention the configuration file
                        self.assertNotIn(
                            "configuration", test.get_stdout(),
                            f"Setup mentioned configfile when {no_config} was provided, function: {test_context}")

                        # Check (by name and directory structure) that the expected files/folders were produced
                        self.assertEqual(helpers.get_dir_tree('./cwl'),
                                         self.expected_cwl_dir_tree,
                                         f"The expected local cwl directory tree was not found, function: {test_context}")
                finally:
                    # Remove the copied workflow files even if an exception was thrown above
                    if os.path.isdir('./cwl'): shutil.rmtree('./cwl')

    """
    Testing that setup-cwl WITH config file mentions the location of the 
    processed input configfile, then copies workflow files. Correctness
    of processed config file will be checked in the setup_config tests.
    """

    def test_setup_cwl_withconfig(self):
        test_functions = [
            helpers.LambdaCapture(lambda: aquatx.setup_cwl(self.aquatx_cwl_path, self.config_file)),
            helpers.ShellCapture(f"aquatx setup-cwl --config {self.config_file}")
        ]
        for test_context in test_functions:
            # So that we may reference the filename in the finally block below
            config_file_location = ""

            try:
                # Execute the given function and capture its stdout stream
                with test_context as test:
                    test()
                    stdout_result = test.get_stdout()
                    # Get the name of the processed config file
                    config_file_location = stdout_result.splitlines()[1].split(": ")[1]

                # Check that the function mentioned the config file with a complete name
                self.assertRegex(stdout_result,
                                 r'The processed configuration file is located at: \d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}_run_config\.yml',
                                 f"Setup failed to mention the location of the processed config file. Function: {test_context}")

                # Check that the processed configuration file exists
                self.assertTrue(os.path.isfile(config_file_location),
                                f"The processed config file does not exist: {config_file_location}. Function: {test_context}")
                os.remove(config_file_location)

                # Check (by name and directory structure) that the expected files/folders were produced
                self.assertDictEqual(helpers.get_dir_tree('./cwl'),
                                 self.expected_cwl_dir_tree)
            finally:
                # Remove the copied workflow files even if an exception was thrown above
                if os.path.isdir('./cwl'): shutil.rmtree('./cwl')
                # Remove the output config file
                if os.path.isfile(config_file_location): os.remove(config_file_location)

    """
    Test that run invocation produces a cwltool subprocess. Since subprocess.run() 
    is a blocking call, we need to call aquatx.run() in its own thread so we can 
    measure its behavior. Otherwise we would have to wait for the whole pipeline 
    to finish before being able to measure it here, and by that time the relevant 
    subprocesses would have already exited. The post-install command accomplishes
    the same thing but in another process rather than another thread.
    """

    def test_run(self):
        # Non-blocking test functions (invocations continue to run in background until test_context is left)
        test_functions = [
            helpers.LambdaCapture(lambda: aquatx.run(self.aquatx_cwl_path, self.config_file), blocking=False),
            helpers.ShellCapture(f"aquatx run --config {self.config_file}", blocking=False)
        ]

        def get_children():
            return psutil.Process(os.getpid()).children(recursive=True)

        for test_context in test_functions:
            with test_context as test:
                test()

                # Check for cwltool in child processes up to 5 times, waiting 1 second in between
                for i in range(10):
                    time.sleep(1)
                    sub_names = [sub.name() for sub in get_children()]
                    if 'cwltool' in sub_names:
                        break

                self.assertIn('cwltool', sub_names,
                              f"The cwltool subprocess does not appear to have started. Function: {test_context}")

    """
    A very minimal test for the subprocess context manager that is used
    to execute post-install aquatx commands via a shell.
    """

    def test_ShellCapture_helper(self):
        # Test blocking capture with stdout (though we can still check stderr with a blocking capture...)
        with helpers.ShellCapture('echo "Today is the day"') as fn:
            # Pre-execution test
            self.assertFalse(fn.is_complete())
            self.assertEqual(fn.get_stdout(), '')
            self.assertEqual(fn.get_stderr(), '')
            self.assertEqual(fn.get_exit_status(), None)

            fn()
            self.assertTrue(fn.is_complete())
            self.assertEqual(fn.get_stdout(), "Today is the day\n")
            self.assertEqual(fn.get_stderr(), '')
            self.assertEqual(fn.get_exit_status(), 0)

        # Test non-blocking capture with stderr (though we can still check stdout with a non-blocking capture...)
        with helpers.ShellCapture('echo "Today was not the day" > /dev/stderr && sleep 1', blocking=False) as fn:
            # Pre-execution test
            self.assertFalse(fn.is_complete())
            self.assertEqual(fn.get_stdout(), '')
            self.assertEqual(fn.get_stderr(), '')
            self.assertEqual(fn.get_exit_status(), None)

            fn()
            self.assertFalse(fn.is_complete())
            time.sleep(1)
            self.assertEqual(fn.get_stdout(), '')
            self.assertEqual(fn.get_stderr(), "Today was not the day\n")
            self.assertEqual(fn.get_exit_status(), 0)
            self.assertTrue(fn.is_complete())

    """
    A very minimal test for the function context manager that is used
    to execute pre-install invocations of aquatx Python functions
    """

    def test_LambdaCapture_helper(self):
        # Test stdout capture
        with helpers.LambdaCapture(lambda: print("Today is the day")) as fn:
            # Pre-execution test
            self.assertFalse(fn.is_complete())
            self.assertEqual(fn.get_stdout(), '')
            self.assertEqual(fn.get_stderr(), '')

            fn()
            self.assertTrue(fn.is_complete())
            self.assertEqual(fn.get_stdout(), "Today is the day\n")
            self.assertEqual(fn.get_stderr(), '')

        # Test stderr capture
        with helpers.LambdaCapture(lambda: print("Today wasn't the day", file=sys.stderr)) as fn:
            # Pre-execution test
            self.assertFalse(fn.is_complete())
            self.assertEqual(fn.get_stdout(), '')
            self.assertEqual(fn.get_stderr(), '')

            fn()
            self.assertTrue(fn.is_complete())
            self.assertEqual(fn.get_stdout(), '')
            self.assertEqual(fn.get_stderr(), "Today wasn't the day\n")

        # Test non-blocking execution
        with helpers.LambdaCapture(lambda: time.sleep(1), blocking=False) as fn:
            fn()
            self.assertFalse(fn.is_complete())
            time.sleep(2)
            self.assertTrue(fn.is_complete())
