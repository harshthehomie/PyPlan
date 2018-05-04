import sys
import os

# print(sys.path)
print(os.environ.get('PYTHONPATH', ''))
for p in sys.path:
    print(p)