# Lifecycle Open Science (LOS) user classification
# classify users as champion, active, emerging, or novice

library(readr)
library(tidyverse)
library(dplyr)
library(stringr)
library(lubridate)

# database backups often include a few days from the new month
# set cutoff_date as the first day of the next month to filter out all later data
classify_users <- function(nps_data_path, cutoff_date) {
  
  user_categories <- read_csv(nps_data_path) %>%
    subset(u.date_confirmed < cutoff_date) %>%
    rowwise() %>%
    mutate(los_project = ifelse(public_projects > 0, T, F),
           los_registration = ifelse(public_registrations > 0 | embargoed_registrations > 0, T, F),
           los_preprint = ifelse(published_preprints > 0, T, F)) %>%
    mutate(
      user_type = case_when(
        sum(los_project, los_registration, los_preprint) == 3 ~ "champion",
        sum(los_project, los_registration, los_preprint) == 2 ~ "active",
        sum(los_project, los_registration, los_preprint) == 1 ~ "emerging",
        TRUE ~ "novice"
      )
    ) %>%
    group_by(user_type) %>%
    summarize(user_count = n())
  
  return(user_categories)
}

# example usage
# update file paths below to match local file locations 
user_categories_2025_02 <- classify_users("~/Desktop/nps_users_2025-03-07.csv", 
                                          "2025-03-01")