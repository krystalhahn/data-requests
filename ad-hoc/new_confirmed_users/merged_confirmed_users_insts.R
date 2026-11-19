library(readr)
library(tidyverse)
library(dplyr)

# create function ----
merge_confirmed_users_insts <- function(confirmed_users_path, nps_insts_path, output_path) {
  
  aggregated_insts <- read_csv(nps_insts_path) %>%
    group_by(u._id) %>%
    summarize(institutions = paste(unique(institution_name), collapse = ", "))
  
  read_csv(confirmed_users_path,
           show_col_types = FALSE,
           col_types = cols(
             .default = col_guess(),
             `u.academiaInstitution` = col_character(),
             `u.academiaProfileID` = col_character(),
             `u.baiduScholar` = col_character(),
             `u.github` = col_character(),
             `u.impactStory` = col_character(),
             `u.linkedIn` = col_character(),
             `u.profileWebsites` = col_character(),
             `u.researchGate` = col_character(),
             `u.researcherId` = col_character(),
             `u.scholar` = col_character(),
             `u.ssrn` = col_character(),
             `u.twitter` = col_character()
           )) %>%
    left_join(aggregated_insts, by = "u._id") %>%
    select(u._id, u.username, u.date_confirmed, u.date_last_login, u.date_last_action, u.fullname, u.given_name, u.middle_names, u.family_name, u.orcid, u.is_active, u.is_spam, u.deleted, institutions, everything()) %>%
    write_csv(., output_path)
  
}

# example usage
# update the file paths below to match local file locations
merge_confirmed_users_insts("~/Desktop/new_confirmed_users_1109.csv",
                      "~/Desktop/nps_users_insts_1109.csv",
                      "~/Desktop/new_confirmed_users_2026-11-09.csv")
