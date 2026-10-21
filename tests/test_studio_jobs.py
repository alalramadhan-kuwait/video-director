"""Job admission and retry regressions; no media tools or network needed."""
from tests import _guard  # noqa: F401
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from director.studio import jobs
from director.studio.store import Studio, Refused


class TestJobAdmission(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.studio = Studio(Path(self.tmp.name))
        self.pid = self.studio.act(None, 'create_project', {
            'title': 'Job test', 'idea': 'Test', 'brand': 'timekeeper',
        })['project']

    def start(self, fn, **kwargs):
        return jobs.start(self.studio, self.pid, 'test', 'draft', 'test job', 0, fn, **kwargs)

    def test_retry_after_completion_returns_original_job(self):
        calls = []
        fn = lambda *args: calls.append('called')
        first = self.start(fn, sync=True, request_id='retry')
        second = self.start(fn, sync=True, request_id='retry')
        self.assertEqual(first, second)
        self.assertEqual(calls, ['called'])
        self.assertEqual(len(self.studio.state(self.pid)['jobs']), 1)
        self.assertEqual(self.studio.jobs, {})

    def test_concurrent_requests_start_only_one_worker(self):
        release = threading.Event()
        ready = threading.Barrier(8)
        def worker(*args):
            release.wait(timeout=10)
        def submit(_):
            ready.wait(timeout=5)
            try:
                return self.start(worker)
            except Refused:
                return None
        try:
            with ThreadPoolExecutor(max_workers=8) as pool:
                results = list(pool.map(submit, range(8)))
            self.assertEqual(sum(r is not None for r in results), 1)
            self.assertEqual(len(self.studio.state(self.pid)['jobs']), 1)
        finally:
            workers = [t for t in threading.enumerate() if t.name in self.studio.jobs]
            release.set()
            for thread in workers:
                thread.join(timeout=5)
                self.assertFalse(thread.is_alive())

    def test_admission_obeys_studio_lock(self):
        # Deterministically assert the check itself is protected, not just event writing.
        original = self.studio.state
        def guarded_state(pid):
            acquired = []
            def probe():
                got = self.studio.lock.acquire(blocking=False)
                acquired.append(got)
                if got:
                    self.studio.lock.release()
            thread = threading.Thread(target=probe)
            thread.start()
            thread.join(timeout=5)
            self.assertEqual(acquired, [False])
            return original(pid)
        with patch.object(self.studio, 'state', side_effect=guarded_state):
            self.start(lambda *args: None, sync=True)

    def test_other_action_request_id_is_refused(self):
        # Reuse a request belonging to this project.
        receipt = self.studio.events(self.pid)[0]['data']['request_id']
        with self.assertRaises(Refused):
            self.start(lambda *args: self.fail('must not run'), sync=True, request_id=receipt)
        self.assertEqual(self.studio.jobs, {})
