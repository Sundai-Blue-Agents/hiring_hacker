# Add this at the very beginning of msf_blue_agents.py, before any other imports
import sys
import importlib.util

# Check if pysqlite3 is available
if importlib.util.find_spec("pysqlite3") is not None:
    import pysqlite3
    # Replace sqlite3 with pysqlite3 in sys.modules
    sys.modules["sqlite3"] = pysqlite3
    print("Successfully replaced sqlite3 with pysqlite3")
else:
    print("Warning: pysqlite3 not found. Using system sqlite3 which may cause issues.")

# The rest of the imports and code should follow...
