"""Offline release gates. NASA submissions and hosted writes are never executed here."""

import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path

import pandas as pd
import pytest
from nasa_fixture import manifest
