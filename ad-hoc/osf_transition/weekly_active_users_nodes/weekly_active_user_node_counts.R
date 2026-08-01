library(readr)
library(tidyverse)
library(dplyr)
library(stringr)
library(googlesheets4)
library(tibble)
library(purrr)
library(tidyr)

# created ----
## from 'created' field ----
nodes_created_field <- read_csv("~/Desktop/weekly_nodes_created_from_field.csv")

## from logs ----
# 'node_created', 'project_created', 'project_created_from_draft_reg', 'created_from'
nodes_created_logs <- read_csv("~/Desktop/weekly_nodes_created_from_logs.csv",
                               col_types = cols(
                                 date_node_created_log = col_datetime(),
                                 date_project_created_log = col_datetime(),
                                 date_created_from_log = col_datetime()
                               ))
# includes both osf.node and osf.registration

### only at osf.node ----
filtered_nodes_created_logs <- nodes_created_logs %>% filter(abstractnode_type == "osf.node")

created_logs_not_field <- filtered_nodes_created_logs %>% filter(!node_id %in% nodes_created_field$node_id)
# 'created' value is before week start but there are relevant logs in week range

created_field_not_logs <- nodes_created_field %>% filter(!node_id %in% filtered_nodes_created_logs$node_id)
# 'created' value in week range but relevant logs fall right after week cutoff

# count nodes with each relevant log
filtered_nodes_created_logs %>%
  summarise(across(
    starts_with("has_"),
    ~ sum(.x, na.rm = TRUE)
  )) %>%
  pivot_longer(
    everything(),
    names_to = "log_type",
    values_to = "count"
  )

# deleted ----
## from 'deleted' field ----
nodes_deleted_field <- read_csv("~/Desktop/weekly_nodes_deleted_from_field.csv")

## from logs ----
# 'node_removed', 'project_deleted', 'confirm_spam'
nodes_deleted_logs <- read_csv("~/Desktop/weekly_nodes_deleted_from_logs.csv")
# includes both osf.node and osf.registration

### only at osf.node ----
filtered_nodes_deleted_logs <- nodes_deleted_logs %>% filter(abstractnode_type == "osf.node")

deleted_field_not_logs <- nodes_deleted_field %>% filter(!node_id %in% filtered_nodes_deleted_logs$node_id)
# 'deleted' value in week range but no relevant logs in week range 
# and in some cases, no relevant logs ever
# many of these were deleted very soon after being created and have no logs other than 'project_created'

deleted_logs_not_field <- filtered_nodes_deleted_logs %>% filter(!node_id %in% nodes_deleted_field$node_id)
# 'node_removed' log in the week range but no 'deleted' datetime for some reason

# count nodes with each relevant log
filtered_nodes_deleted_logs %>%
  summarise(across(
    starts_with("has_"),
    ~ sum(.x, na.rm = TRUE)
  )) %>%
  pivot_longer(
    everything(),
    names_to = "log_type",
    values_to = "count"
  )
