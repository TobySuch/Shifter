# Changelog

## [0.9.0](https://github.com/TobySuch/Shifter/compare/v0.8.0...v0.9.0) (2026-11-10)


### Features

* calculate file hashes in a background task ([#823](https://github.com/TobySuch/Shifter/issues/823)) ([9968a6c](https://github.com/TobySuch/Shifter/commit/9968a6c348261ee920954e59d9b0ab2860707bcf))
* chunked uploads with streaming zips and a progress bar ([#822](https://github.com/TobySuch/Shifter/issues/822)) ([9531fe6](https://github.com/TobySuch/Shifter/commit/9531fe6b52c9d501a7dda06cf72b5996f60620a8))
* delete expired files with tasks scheduled at their expiry ([#828](https://github.com/TobySuch/Shifter/issues/828)) ([43f1694](https://github.com/TobySuch/Shifter/commit/43f1694c9e969ebba1e57cd07ee2acc1d44a033c))
* drop the files awaiting hash count from site information ([#834](https://github.com/TobySuch/Shifter/issues/834)) ([a9a23dd](https://github.com/TobySuch/Shifter/commit/a9a23ddea59598b4252e84678d3ebee413940c57))
* make automatic task history pruning an optional site setting ([#837](https://github.com/TobySuch/Shifter/issues/837)) ([e3efedb](https://github.com/TobySuch/Shifter/commit/e3efedb72f1d052adfde2d59984a1e37d3a27bd8))
* optionally hand downloads to the reverse proxy ([#832](https://github.com/TobySuch/Shifter/issues/832)) ([9df47da](https://github.com/TobySuch/Shifter/commit/9df47da3326b50d70911243641389130702ff6a6))
* paginate the task log by 20 tasks ([#838](https://github.com/TobySuch/Shifter/issues/838)) ([bd961ca](https://github.com/TobySuch/Shifter/commit/bd961ca917ba7d23279188645fd1fd9b26adc407))
* remove the single-request upload POST ([#827](https://github.com/TobySuch/Shifter/issues/827)) ([32ddec1](https://github.com/TobySuch/Shifter/commit/32ddec1ab2e56a794de4878c97bf110cda7af39f))
* render the upload page as a React island ([#820](https://github.com/TobySuch/Shifter/issues/820)) ([d2105ae](https://github.com/TobySuch/Shifter/commit/d2105ae2f86de13de5fab3c92f77c8e5edf05474))
* replace the cron job with scheduled tasks ([#829](https://github.com/TobySuch/Shifter/issues/829)) ([a087450](https://github.com/TobySuch/Shifter/commit/a08745037bdd9c6cc518adf2bf5991f499ee3f2a))
* show a task log and task stats in site settings ([#824](https://github.com/TobySuch/Shifter/issues/824)) ([1539cef](https://github.com/TobySuch/Shifter/commit/1539cef0aaea2a90530bc758e9622e814cd08a80))
* show when finished tasks completed in the task log ([#836](https://github.com/TobySuch/Shifter/issues/836)) ([cdb3925](https://github.com/TobySuch/Shifter/commit/cdb3925ebd8a912c992792c4e0250dbb60d630c4))
* sort the task log by scheduled time ([#835](https://github.com/TobySuch/Shifter/issues/835)) ([15c5446](https://github.com/TobySuch/Shifter/commit/15c54464a9cdcbfd947251185809f7dd9ad694d2))
* support units in site settings and default to 2W/1M expiry ([#833](https://github.com/TobySuch/Shifter/issues/833)) ([54b02fa](https://github.com/TobySuch/Shifter/commit/54b02fa3b6318ed4cd8ef7fa3103a16db971dc76))


### Bug Fixes

* serve requests with threaded gunicorn workers ([#831](https://github.com/TobySuch/Shifter/issues/831)) ([117aeb6](https://github.com/TobySuch/Shifter/commit/117aeb6ca969da3f5b7032c76f92692b049f7a0b))

## [0.8.0](https://github.com/TobySuch/Shifter/compare/v0.7.0...v0.8.0) (2026-11-08)


### Features

* add edit expiry date feature ([#643](https://github.com/TobySuch/Shifter/issues/643)) ([b7f553b](https://github.com/TobySuch/Shifter/commit/b7f553ba875d11037e34c27f7c2636c46455d40d))
* add Release Please, semantic versioning, and PR title linting ([d532707](https://github.com/TobySuch/Shifter/commit/d532707fcb00a97e50f8a209e499d6db9c4f219a))


### Bug Fixes

* remove unreliable site information test ([#689](https://github.com/TobySuch/Shifter/issues/689)) ([c3992c2](https://github.com/TobySuch/Shifter/commit/c3992c2f56443a3a85730e8f8a50b05a16786c5d))
* rename release-please config to remove leading dot ([ec9d215](https://github.com/TobySuch/Shifter/commit/ec9d215d8f29d525d05b696af1abd9e2f58d9c3e))
* return 404 for expired files on direct download view (GHSA-26gp-m28h-g3hw) ([#818](https://github.com/TobySuch/Shifter/issues/818)) ([7275c4f](https://github.com/TobySuch/Shifter/commit/7275c4f8dbe2e0847395340bd860170a387fb08e))
* use GitHub App token in release-please workflow to trigger CI ([#688](https://github.com/TobySuch/Shifter/issues/688)) ([871c30d](https://github.com/TobySuch/Shifter/commit/871c30d44826cade33e0889588d754a6198eb4f8))
