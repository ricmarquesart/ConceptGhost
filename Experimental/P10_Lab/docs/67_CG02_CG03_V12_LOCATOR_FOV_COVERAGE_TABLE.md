# CG-02 / CG-03 Panorama v1.2 — Locator UX + FOV Coverage Table

## Locator BAT behavior

A missing `LATEST_P10_RUN.json` is not a panorama failure. It normally means Workflow 02 has not been queued since the latest install/restart.

`04_OPEN_LATEST_P10_RESULTS.bat` now reports this as **INFO** and shows the exact locator path checked.

## FOV → source coverage quick table

Approximate ERP-width coverage:

- **18°** ≈ **5%**
- **60°** ≈ **16.7%**
- **90°** ≈ **25%**
- **120°** ≈ **33.3%**
- **144°** ≈ **40%**

Target about **40%** → **`h_fov_deg ≈ 144°`**.

The workflow contains a large highlighted note named:

`FOV → SOURCE COVERAGE QUICK TABLE · 144° ≈ 40%`

## Authority warning

Node 1181 provides the accepted P9 camera FOV to Node 36. A manual override on Node 36 is experimental. If it diverges from the accepted P9 camera, CG-03 reprojection error can increase.

## Release

- Drive file ID: `13c5PZcVoX17QlrGwrqHFF-NTW20mf7ly`
- SHA-256: `f95dbe1381960b0f027d30b1ef112453f76d7da6de9ed7ee1eaa5de952a16119`
