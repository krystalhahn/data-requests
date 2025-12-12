# User group metrics (nps_users)

### 1. `nps_users.py`
Run `write_nps_users_csv()` to get all user data

Output: `nps_users_[MMYY].csv`*

### 2. `nps_users_institutions.py`
Run `write_nps_users_insts()` to get all OSFI affiliated user data

Output: `nps_insts_[MMYY].csv`*

### 3. `merged_nps_users_insts.R`
Use `merge_nps_users_insts()` to merge the outputs of #1 and #2 for the final `nps_users.csv` dataset

Output: `nps_users_[MM-DD-YY].csv`*
### 4. `los_user_classification.R`
Use `classify_users()` to classify users as LOS overall and within OSFI affiliated users

Output: no .csv output, but used to update the [LOS sheet](https://docs.google.com/spreadsheets/d/1Swu1y0S5IAW9tO6P-0hF9-jU7fWRZ_fyogjguDWbkhI/edit?gid=2142473306#gid=2142473306)
___

\* I use MMYY in the filenames of intermediate files (`nps_users_[MMYY].csv` and `nps_insts_[MMYY].csv`) to help differentiate them from the final merged `nps_users_[MM-DD-YY].csv`, but this is up to personal preference
