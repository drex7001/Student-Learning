"""Disengagement early-support risk engine.

``dropout_ews_bn`` is the discrete Bayesian network described in
``research/dropout-ews/REPORT.md``. It is vendored here unchanged so the API and the
research build scripts share exactly one copy of the model and its parameters.

Read ``research/dropout-ews/README.md`` before changing anything in this package. The
model carries hard constraints that are enforced in code and covered by tests:

* ``Neuro_Type`` has no direct edge to the outcome.
* ``do()`` is restricted to :data:`~app.risk.dropout_ews_bn.MODIFIABLE_NODES`; anything
  else raises ``NonModifiableInterventionError``, which the API maps to HTTP 403.
* No CPD entry is exactly 0 or 1.
* Every inference result carries its provenance, caveat and parameter fingerprint.
"""

from __future__ import annotations
