library(readr)
library(tidyverse)
library(dplyr)

# create function ----
merge_nps_users_insts <- function(nps_users_path, nps_insts_path, output_path) {
  
  aggregated_insts <- read_csv(nps_insts_path) %>%
    group_by(u._id) %>%
    summarize(institutions = paste(unique(institution_name), collapse = ", "))
  
  read_csv(nps_users_path) %>%
    left_join(aggregated_insts, by = "u._id") %>%
    select(u._id, u.username, u.date_confirmed, u.date_last_login, u.date_last_action, institutions, everything()) %>%
    write_csv(., output_path)

}

# example usage
# update the file paths below to match local file locations
merge_users_insts("~/Desktop/nps_users_1202.csv",
                  "~/Desktop/nps_users_insts_1202.csv",
                  "~/Desktop/nps_users_2025-12-02.csv")