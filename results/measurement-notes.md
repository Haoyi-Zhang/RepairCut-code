# Measurement notes

The retained original validation campaign ran seven scientific child processes sequentially with one worker. Their suite JSON records 5.275391517 aggregate CPU seconds, 5.290027825999914 aggregate wall seconds, and 94,508 KiB maximum child-reported RSS; the circuits suite records 2.74431932 CPU seconds. These values are also summarized in `cpu-accounting.json`.

A clean-extraction reproduction records its own parent/child timing and memory separately. Neither resource record is an equality target for the other or for another platform. Scientific equality is defined by regenerated CSV rows and declared JSON counts. At intake the environment had no swap; each scientific child used the documented 3 GiB virtual-address, 35 CPU-second, 40 wall-second, and exact-row admission guards.
