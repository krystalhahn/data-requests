# Impact of trainings on Lifecycle Open Science (LOS)

### 1. `nps_names_orcids.py`
- Run `write_nps_users_names_orcids()` to get name and ORCID data to supplement existing NPS data

Output: `nps_users_names_orcids.csv`*

### 2. `trainings_data_prep.R`
- Compile Qualtrics data from different trainings/trainings groups
- Match training participants to OSF profiles (wherever possible)

Output: `osf_participants`*

### 3. `nps_data_prep.R`
- Compile NPS and LOS data from relevant months to calculate change relative to trainings

Output: `los_list`*

### 4. `trainings_analysis.R` (Preliminary analysis)
- Segment matched users into NPS and LOS metrics to evaluate change after training
- Evaluate change in logged activity after training
- Map actions to training topics
- Generate preliminary visualizations

Output: Many output dataframes and visualizations
