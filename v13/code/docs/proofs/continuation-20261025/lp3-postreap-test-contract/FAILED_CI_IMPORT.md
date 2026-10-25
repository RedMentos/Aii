# Failed attempt preserved — CI path error (2026-10-25)

- First CI run: https://github.com/RedMentos/Aii/actions/runs/40184017321
- Job `121140859074`; source `9de769c3ffa3c770d41d112b243aac570a9a9452`.
- Exact Run20 archive SHA and Run21 patched helper SHA both PASS.
- **ERROR** before test body: `ModuleNotFoundError: No module named 'test_lp3_serial_review_run18'`. Workflow PYTHONPATH contained archived helper test directory but omitted current `v13/code/tests`.
- Raw artifact `12595356418`, ZIP SHA256 `9f48dee2903eee704a68972ed83f91a106c9f10a194d41f4265ee3cd4e5693ff`.
- This failure is environment/import setup, not a passed LP3 process proof. No native model or cgroup writes.
- Correction: `5ef31957bdf0cee2a410c05f62c1628806806bb8` includes current tests path. Re-run must prove actual test body.
