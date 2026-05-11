library(readr)
library(tidyverse)
library(dplyr)
library(stringr)
library(googlesheets4)
library(tibble)
library(purrr)
library(tidyr)

node_children_list <- read_csv("~/Desktop/project_statuses_children_0504_ext.csv")

# just projects/roots (not components)
# only registrations (already only registrations, but leave type in for requester)
project_children_list <- node_children_list %>%
  filter(is_root) %>%
  select(-content_type_pk)

write_csv(project_children_list, "~/Desktop/child_node_count_by_privacy_2026-05-04.csv")
