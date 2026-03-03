"""
Imports all of the routers 
(files that hold all of the api endpoints for our backend) 
the api folder is a package, and the routers folder is a subpackage
that just means you can import it somewhere else
that means this file runs whenever you see from api.routers import xxx
"""
from . import models, runs, system

__all__ = ["models", "runs", "system"]
