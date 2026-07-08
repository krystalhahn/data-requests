library(readr)
library(tidyverse)
library(dplyr)
library(stringr)
library(googlesheets4)
library(tibble)
library(purrr)
library(tidyr)

gfs_regs <- read_csv("~/Desktop/gfs_regs_with_active_nodes_0704.csv")
# 829

table(gfs_regs$reg_is_public, is.na(gfs_regs$linked_node_id))
# 346 public regs have linked nodes 
# 0 public regs don't have linked nodes
# 123 private regs have linked nodes
# 360 private regs don't have linked nodes

# inspect registrations with no linked nodes ----
no_linked_nodes <- gfs_regs %>% filter(is.na(linked_node_id))

table(no_linked_nodes$reg_is_public)
# all private

# of the private regs with no linked nodes
table(no_linked_nodes$reg_moderation_state)
# initial  pending rejected reverted 
# 42        1      288       29 

table(no_linked_nodes$reg_embargo_state)
# moderator_rejected pending_moderation           rejected 
# 147                  1                 34 

# of the 469 registrations that have linked nodes,
# logged activity in the last 3 months ----
table(gfs_regs$node_is_active_3_mo)
# FALSE  TRUE 
# 394    75 

# logged activity in the last year ----
table(gfs_regs$node_is_active_1_yr)
# FALSE  TRUE 
# 156   313 

# after excluding system logs ----
gfs_regs_nosyslogs <- read_csv("~/Desktop/gfs_regs_with_active_nodes_0704_nosyslogs.csv")

cols <- names(gfs_regs_nosyslogs)[names(gfs_regs_nosyslogs) != "reg_id"]

for (col in cols) {
  test_col <- gfs_regs_nosyslogs %>% arrange(reg_id) %>% pull(col)
  gfs_col <- gfs_regs %>% arrange(reg_id) %>% pull(col)
  if (!identical(test_col, gfs_col)) {
    cat("Column differs:", col, "\n")
  }
}
# Column differs: node_is_active_3_mo 
# Column differs: node_is_active_1_yr 

table(gfs_regs_nosyslogs$node_is_active_3_mo)
# FALSE  TRUE 
# 406    63 

table(gfs_regs_nosyslogs$node_is_active_1_yr)
# FALSE  TRUE 
# 219   250

# rows where node_is_active_3_mo differs
inner_join(gfs_regs_nosyslogs, gfs_regs, by = "reg_id", suffix = c("_test", "_gfs")) %>%
  filter(node_is_active_3_mo_test != node_is_active_3_mo_gfs) %>%
  select(reg_id, node_is_active_3_mo_test, node_is_active_3_mo_gfs)

# rows where node_is_active_1_yr differs
inner_join(gfs_regs_nosyslogs, gfs_regs, by = "reg_id", suffix = c("_test", "_gfs")) %>%
  filter(node_is_active_1_yr_test != node_is_active_1_yr_gfs) %>%
  select(reg_id, node_is_active_1_yr_test, node_is_active_1_yr_gfs)
