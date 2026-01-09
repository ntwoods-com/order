"""WSGI entrypoint for PythonAnywhere.

In PythonAnywhere Web tab -> WSGI configuration file, you can point to this module
or import `application` from it.
"""

from app import app as application
