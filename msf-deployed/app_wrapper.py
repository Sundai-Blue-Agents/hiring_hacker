# This wrapper ensures pysqlite3 is properly set up before importing any modules that use sqlite3
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

# Now import and run the main application
from msf_blue_agents import *

# If the main application has a specific entry point, call it here
# For example, if msf_blue_agents.py has a main() function:
# if __name__ == "__main__":
#     main()
