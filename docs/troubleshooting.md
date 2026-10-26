# Troubleshooting

## A file is reported as changed

Another program modified its size or timestamp after preview. Refresh the preview and verify the new destination before retrying.

## A destination already exists

FileForge will not overwrite it. Change the rule, move the existing file manually, or select another organization/quarantine folder.

## Windows reports a locked file

Close applications using the file and retry. If a multi-file operation had started, FileForge attempts rollback and records the outcome in History.

## A `.fileforge-*.pending` file remains

This indicates the process and its rollback were interrupted or the filesystem rejected recovery. Do not delete it blindly: compare its size and contents with the History entry, then restore it to the recorded source path only if that path is free.

## Duplicate scanning is slow

Only same-sized files are hashed, but large duplicate candidates still require full reads. Cancel safely from the Duplicates tab and narrow the selected roots if needed.

## The application does not start

For source installs, confirm Python 3.11+ and reinstall with `python -m pip install .`. For packaged builds, retain the complete `FileForge` bundle; the executable depends on adjacent Qt libraries.
