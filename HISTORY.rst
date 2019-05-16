History
=======

0.3.0 (2019-05-16)
------------------
* Cleaned up shutdown code
* Create retry logic throughout to deal with disconnect and other failures
* Added functionality to deal with state maintenance
* Updated dependencies
* Removed flaky test

0.2.1 (2019-02-02)
------------------
* Made websocket library usage backwards-compatible with older versions

0.2.0 (2019-02-02)
------------------
* Rewrote discovery to use multiple threads so it only takes 1 second
* Improved logging in client class with logger passed through
* Improved handling of event loop to allow usage within existing async codebase
* Added --version argument to CLI

0.1.7 (2019-02-01)
------------------
* Migrated from bumpversion to bump2version for cleaner release process

0.1.6 (2019-02-01)
------------------
* Another bump to let Travis upload to PyPi itself, to fix the build 

0.1.5 (2019-02-01)
------------------
* Bumped version after tweaking build workflow

0.1.4 (2019-01-31)
------------------

* Tweaked various build and testing parameters to get code coverage and distribution working

0.1.3 (2019-01-31)
------------------

* Updated README layout
* Added coveralls config for travis and CHANGELOG/HISTORY link

0.1.2 (2019-01-31)
------------------

* Fixed documentation build for ReadTheDocs
* Fixed restructuredtext in history which was breaking PyPi formatting

0.1.1 (2019-01-30)
------------------

* Improved discovery logging
* Added documentation
* Fixed tests

0.1.0 (2019-01-27)
------------------

* First release on PyPI.
* Basic functional CLI client, to allow basic control (on, off, check state)
* Added comprehensive logging with verbosity option to help debug new devices
* Control of device is via async websocket, so should be usable in async code
