# Spike in GUID minting trends/file activity

### 1. `target_object_creators.py`
- Run `get_target_creators()` to get the creator of the target object of file GUIDs created in specified months

Output: `target_creators.csv`

### 2. `latest_version_creators.py`
- Run `get_latest_version_creators()` to get the creator of the most recent/top-level version of file GUIDs created in specified months

Output: `latest_version_creators.csv`

### 3. `minted_version_creators.py`
- Run `get_minted_version_creators()` to get the creator of the version at the time of GUID minting of file GUIDs created in specified months

Output: `minted_version_creators.csv`

### 4. `file_guids_creators.py`
- Run `inspect_file_guids()` to inspect file GUIDs created in specified months
- Run `inspect_file_guids_creators()` to inspect file GUIDs as well as their creators (target object, latest version, minted version)
- Run `find_files_with_multiple_guids()` to find cases in which files have multiple associated GUIDs

Output: `file_guids.csv`, `file_guids_creators.csv`, `files_with_multiple_guids.csv`

### 5. `guid_investigation.py`
- Evaluate distribution of files for target object creators, latest version creators, and minted version creators comparing June-July and Aug-Sept 2025
- Validate creator-level data (in progress)
- Inspect empty file GUIDs and prevalence in month ranges

Output: Various output dataframes
