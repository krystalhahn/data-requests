library(readr)
library(tidyverse)
library(dplyr)
library(stringr)
library(googlesheets4)
library(tibble)
library(purrr)
library(tidyr)
gs4_auth(email = "krystal@cos.io", cache = FALSE)

# get all of NPS/LOS data for other months ----
# to calculate change based on training_date

# one unified function for classification (accounting for differences like pre-contributor columns, institutions)
classify_participants <- function(target_users, nps_data_path, cutoff_date,
                                  include_created = FALSE,
                                  include_institutions = FALSE) {
  
  nps_data <- readr::read_csv(nps_data_path) %>%
    subset(u.date_confirmed < cutoff_date) %>%
    select(-u.username, -u.date_confirmed)
  
  # join users
  npslos <- target_users %>%
    left_join(nps_data, by = "u._id")
  
  # rename base columns to _created if needed
  if (!include_created) {
    npslos <- npslos %>%
      rename_with(~ paste0(.x, "_created"), 
                  c("public_projects", "private_projects",
                    "public_registrations", "withdrawn_registrations", "embargoed_registrations", 
                    "published_preprints", "withdrawn_preprints"))
  }
  
  # compute LOS flags
  npslos <- npslos %>%
    rowwise() %>%  # allows sum() per row
    mutate(
      los_project = public_projects_created > 0,
      los_registration = public_registrations_created > 0 |
        embargoed_registrations_created > 0,
      los_preprint = published_preprints_created > 0,
      user_type = case_when(
        is.na(public_projects_created) &
          is.na(public_registrations_created) &
          is.na(embargoed_registrations_created) &
          is.na(published_preprints_created) ~ NA_real_,
        sum(los_project, los_registration, los_preprint) == 3 ~ 4,
        sum(los_project, los_registration, los_preprint) == 2 ~ 3,
        sum(los_project, los_registration, los_preprint) == 1 ~ 2,
        TRUE ~ 1
      )
    ) %>%
    ungroup()
  
  # add institutions flag if requested
  if (include_institutions) {
    npslos <- npslos %>%
      mutate(is_institutional = !is.na(institutions) & institutions != "")
  }
  
  # keep only relevant columns
  npslos <- npslos %>%
    select(u._id, where(is.numeric))
  # select(Email, u._id, u.username, orcid, where(is.numeric))
  
  return(npslos)
}

# specify parameters for each month's data
run_params <- tribble(
  ~month_label, ~nps_data_path,                                                       ~cutoff_date,  ~include_created, ~include_institutions,
  "0524",       "~/Desktop/script_outputs/nps_users_final/nps_users_2024-06-07.csv",  "2024-06-01",  FALSE,            FALSE,
  "0624",       "~/Desktop/script_outputs/nps_users_final/nps_users_2024-07-10.csv",  "2024-07-01",  FALSE,            FALSE,
  "0724",       "~/Desktop/script_outputs/nps_users_final/nps_users_2024-08-07.csv",  "2024-08-01",  FALSE,            FALSE,
  "0824",       "~/Desktop/script_outputs/nps_users_final/nps_users_2024-09-03.csv",  "2024-09-01",  FALSE,            TRUE,
  "0924",       "~/Desktop/script_outputs/nps_users_final/nps_users_2024-10-07.csv",  "2024-10-01",  FALSE,            TRUE,
  "1024",       "~/Desktop/script_outputs/nps_users_final/nps_users_2024-11-05.csv",  "2024-11-01",  TRUE,             TRUE,
  "1124",       "~/Desktop/script_outputs/nps_users_final/nps_users_2024-12-02.csv",  "2024-12-01",  TRUE,             TRUE,
  "1224",       "~/Desktop/script_outputs/nps_users_final/nps_users_2025-01-02.csv",  "2025-01-01",  TRUE,             TRUE,
  "0125",       "~/Desktop/script_outputs/nps_users_final/nps_users_2025-02-03.csv",  "2025-02-01",  TRUE,             TRUE,
  "0225",       "~/Desktop/script_outputs/nps_users_final/nps_users_2025-03-07.csv",  "2025-03-01",  TRUE,             TRUE,
  "0325",       "~/Desktop/script_outputs/nps_users_final/nps_users_2025-04-07.csv",  "2025-04-01",  TRUE,             TRUE,
  "0425",       "~/Desktop/script_outputs/nps_users_final/nps_users_2025-05-06.csv",  "2025-05-01",  TRUE,             TRUE,
  "0525",       "~/Desktop/script_outputs/nps_users_final/nps_users_2025-06-05.csv",  "2025-06-01",  TRUE,             TRUE,
  "0625",       "~/Desktop/script_outputs/nps_users_final/nps_users_2025-07-07.csv",  "2025-07-01",  TRUE,             TRUE,
  "0725",       "~/Desktop/script_outputs/nps_users_final/nps_users_2025-08-04.csv",  "2025-08-01",  TRUE,             TRUE,
  "0825",       "~/Desktop/script_outputs/nps_users_final/nps_users_2025-09-04.csv",  "2025-09-01",  TRUE,             TRUE,
  "0925",       "~/Desktop/script_outputs/nps_users_final/nps_users_2025-10-06.csv",  "2025-10-01",  TRUE,             TRUE,
)

# run classify_participants() based on parameters automatically
los_list <- pmap(
  list(
    nps_data_path = run_params$nps_data_path,
    cutoff_date = run_params$cutoff_date,
    include_created = run_params$include_created,
    include_institutions = run_params$include_institutions
  ),
  function(nps_data_path, cutoff_date, include_created, include_institutions) {
    classify_participants(osf_participants,
                          nps_data_path = nps_data_path,
                          cutoff_date = cutoff_date,
                          include_created = include_created,
                          include_institutions = include_institutions)
  }
)

names(los_list) <- paste0("los_", run_params$month_label)