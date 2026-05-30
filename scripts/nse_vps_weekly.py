#!/usr/bin/env python3
"""VPS weekly outlook generator."""
import sys, os, warnings
warnings.filterwarnings('ignore')

sys.path.insert(0, os.path.expanduser('~/.hermes/scripts'))
from nse_signal_engine import generate_weekly, accuracy_report

print(generate_weekly())
print()
print(accuracy_report())
