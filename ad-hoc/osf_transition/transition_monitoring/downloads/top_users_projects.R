library(readr)
library(tidyverse)
library(dplyr)
library(stringr)
library(googlesheets4)
library(tibble)
library(purrr)
library(tidyr)

downloads_all <- read_csv("~/Desktop/download_events_0901.csv")

# check only latest week (8/23-8/29)
downloads <- downloads_all %>%
  filter(created >= as.POSIXct("2026-08-23 00:00:00", tz = "UTC"),
         created < as.POSIXct("2026-08-30 00:00:00", tz = "UTC"))

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

# top 10 projects by download count ----
top_projects_by_count <- downloads %>%
  filter(resource_type == "osf.node") %>%
  group_by(resource_guid) %>%
  summarize(total = n(),
            total_gb = round(sum(size_bytes) / 1e9, 2)) %>%
  ungroup() %>%
  filter(!is.na(resource_guid)) %>%
  arrange(desc(total)) %>%
  head(10)

# top 10 projects by total download size (GB) ----
top_projects_by_gb <- downloads %>%
  filter(resource_type == "osf.node") %>%
  group_by(resource_guid) %>%
  summarize(total = n(),
            total_gb = round(sum(size_bytes) / 1e9, 2)) %>%
  ungroup() %>%
  filter(!is.na(resource_guid)) %>%
  arrange(desc(total_gb)) %>%
  head(10)
