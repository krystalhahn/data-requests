library(readr)
library(tidyverse)
library(dplyr)
library(stringr)
library(googlesheets4)
library(tibble)
library(purrr)
library(tidyr)

# storage usage (in bytes) ----
storage_usage <- read_csv("~/Desktop/node_storage_usage_only_0704.csv")

## GB buckets ----
# 5, 10, 25, 50, 100, 500 GBs
storage_usage_buckets <- storage_usage %>%
  rename(storage_usage_b = storage_usage) %>%
  mutate(storage_usage_gb = storage_usage_b / 1e9,
         storage_bucket = case_when(is.na(storage_usage_gb) ~ "0 GB / NA",
                                    storage_usage_gb > 500 ~ ">500 GB",
                                    storage_usage_gb > 100 ~ ">100 GB",
                                    storage_usage_gb > 50 ~ ">50 GB",
                                    storage_usage_gb > 25 ~ ">25 GB",
                                    storage_usage_gb > 10 ~ ">10 GB",
                                    storage_usage_gb > 5 ~ ">5 GB", 
                                    storage_usage_gb <= 5 ~ "<5 GB",
                                    .default = NA
         )) %>%
  group_by(is_public, storage_bucket) %>%
  summarize(node_count = n())

bucket_levels <- c("0 GB / NA", "<5 GB", ">5 GB", ">10 GB", ">25 GB", ">50 GB", ">100 GB", ">500 GB")

write_sheet(storage_usage_buckets %>%
              mutate(storage_bucket = factor(storage_bucket, levels = bucket_levels)) %>%
              arrange(desc(is_public), desc(storage_bucket)), 
            sheet_url, sheet = "storage_usage")