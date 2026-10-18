"""Run several (items, out, selector) jobs in one process so the model and ASR load once.
  python -m arabic_tts.batch ITEMS:OUT:SELECT [ITEMS:OUT:SELECT ...]"""
import sys
from .run import main
for job in sys.argv[1:]:
    items, out, sel = job.split(':')
    print('== JOB', job, flush=True)
    main([items, out, '--select', sel])
print('BATCH DONE', flush=True)
