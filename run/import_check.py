"""Quick import check for key modules.

This script ensures the project root is on sys.path so local packages
like `autonomous` and `simulation` can be imported when executed from
the `run` folder.
"""
import sys, os

# add project root to sys.path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

modules = [
    'autonomous.weaviate_client',
    'autonomous.reasoning_agent',
    'autonomous.crew',
    'crew_agent',
    'data_layer.create_schema',
    'simulation.stimulate_mq4'
]

for m in modules:
    try:
        __import__(m)
        print('OK', m)
    except Exception as e:
        import traceback
        print('ERR', m, type(e).__name__, str(e))
        traceback.print_exc()
