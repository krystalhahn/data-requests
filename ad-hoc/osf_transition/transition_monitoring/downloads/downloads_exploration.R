library(readr)
library(tidyverse)
library(dplyr)
library(stringr)
library(googlesheets4)
library(tibble)
library(purrr)
library(tidyr)
library(jsonlite)

downloads_all <- read_csv("~/Desktop/download_events_0822.csv")

# check only first week (8/9-8/15)
downloads <- downloads_all %>%
  filter(created >= as.POSIXct("2026-08-09 00:00:00", tz = "UTC"),
         created < as.POSIXct("2026-08-16 00:00:00", tz = "UTC"))

unique_users <- nrow(downloads %>% distinct(user_guid))
downloads_from_users <- nrow(downloads %>% filter(!is.na(user_guid)))
downloads_from_nonusers <- nrow(downloads %>% filter(is.na(user_guid)))

# top 10 users by download count ----
top_users_by_count <- downloads %>%
  group_by(user_guid) %>%
  summarize(total = n(),
            total_gb = round(sum(size_bytes) / 1e9, 2)) %>%
  ungroup() %>%
  filter(!is.na(user_guid)) %>%
  arrange(desc(total)) %>%
  head(10)

# top 10 users by total download size (GB) ----
top_users_by_gb <- downloads %>%
  group_by(user_guid) %>%
  summarize(total = n(),
            total_gb = round(sum(size_bytes) / 1e9, 2)) %>%
  ungroup() %>%
  filter(!is.na(user_guid)) %>%
  arrange(desc(total_gb)) %>%
  head(10)

# top 10 resources by download count ----
## nodes, registrations, preprints
top_projects_by_count <- downloads %>%
  group_by(resource_guid) %>%
  summarize(total = n(),
            total_gb = round(sum(size_bytes) / 1e9, 2)) %>%
  ungroup() %>%
  filter(!is.na(resource_guid)) %>%
  arrange(desc(total)) %>%
  head(10)

# top 10 resources by total download size (GB) ----
top_projects_by_gb <- downloads %>%
  group_by(resource_guid) %>%
  summarize(total = n(),
            total_gb = round(sum(size_bytes) / 1e9, 2)) %>%
  ungroup() %>%
  filter(!is.na(resource_guid)) %>%
  arrange(desc(total_gb)) %>%
  head(10)

# by zip_completed for the following ----
# set zip_completed levels for ordering
zip_levels = c(TRUE, FALSE, NA)

# by storage_region ----
downloads_by_storage_region <- downloads %>%
  mutate(zip_completed = factor(zip_completed, levels = zip_levels)) %>%
  group_by(storage_region, zip_completed) %>%
  summarise(total_count = n(),
            total_size_gb = round(sum(size_bytes, na.rm=TRUE) / 1e9, 2),
            .groups = "drop")

# by storage provider ----
downloads_by_provider <- downloads %>%
  mutate(zip_completed = factor(zip_completed, levels = zip_levels)) %>%
  group_by(storage_provider, zip_completed) %>%
  summarise(total_count = n(),
            total_size_gb = round(sum(size_bytes, na.rm=TRUE) / 1e9, 2),
            .groups = "drop") %>%
  complete(
    storage_provider,
    zip_completed,
    fill = list(total_count = 0, total_size_gb = 0)
  )

# by download_type ----
total_by_type <- downloads %>%
  mutate(zip_completed = factor(zip_completed, levels = zip_levels)) %>%
  group_by(download_type, zip_completed) %>%
  summarise(
    total_count = n(),
    total_size_gb = round(sum(size_bytes, na.rm = TRUE) / 1e9, 2),
    .groups = "drop"
  ) %>% arrange(download_type, zip_completed)

# by user type ----
total_by_user_type <- downloads %>%
  mutate(zip_completed = factor(zip_completed, levels = zip_levels)) %>%
  mutate(user_type = case_when(is.na(user_guid) ~ "nonuser",
                               !is.na(user_guid) ~ "user")) %>%
  group_by(user_type, zip_completed) %>%
  summarise(
    total_count = n(),
    total_size_gb = round(sum(size_bytes, na.rm = TRUE) / 1e9, 2),
    .groups = "drop"
  ) %>%
  mutate(total_percent = round(total_count / sum(total_count)*100, 2)) %>%
  arrange(desc(user_type))
