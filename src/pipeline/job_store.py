"""Where job status files and cached results live.

`LocalJobStore` keeps durable atomic files on a persistent host volume. It records
state history and submission checkpoints separately from the canonical API schemas.
"""

import base64
import hashlib
import json
import os
import re
import tempfile
import time
from datetime import datetime
from functools import lru_cache
