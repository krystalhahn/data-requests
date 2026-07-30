library(readr)
library(tidyverse)
library(dplyr)
library(stringr)
library(googlesheets4)
library(tibble)
library(purrr)
library(tidyr)

# node_privacy_file ----
# spreadsheet counting the number of public and private nodes by the number of files associated with them
node_file_list <- read_csv("~/Desktop/node_file_count_0504.csv")

file_count_list <- node_file_list %>%
  group_by(file_count, is_public) %>%
  summarize(n = n(), .groups = "drop") %>%
  pivot_wider(names_from = is_public, values_from = n, values_fill = 0) %>%
  rename(public_node_count = public,
         private_node_count = private) %>%
  mutate(total_node_count = public_node_count + private_node_count)

write_csv(file_count_list, "~/Desktop/node_count_by_file_count_2026-05-04.csv")
