# data/

- `aoi/` - the project boundary (Area Of Interest) as GeoJSON. Small
  file, safe to track in Git.
- Anything raw, downloaded, or large (satellite scenes, exported
  rasters) should **not** be committed - see `.gitignore`. Earth
  Engine exports land in `outputs/` or a scratch folder outside the
  repo.

Demo site selection happens in Phase 1.
