library(readr)
library(tidyverse)
library(dplyr)
library(stringr)
library(googlesheets4)
library(tibble)
library(purrr)
library(tidyr)

# temporary fix for incomplete funder migration until permanent fix is applied in prod release
# it appears that ROR IDs were migrated properly, but some names were not

# read in most recent funder LOS metrics
funder_metrics <- read_sheet(los_sheet_url, sheet = "Funder", skip = 2) %>%
  rename(total_n = `n...4`,
         total_n_change = `n_change...5`,
         total_pct_change = `pct_change...6`,
         outputs_n = `n...7`,
         outputs_n_change = `n_change...8`,
         outputs_pct_change = `pct_change...9`,
         outputs_pct_total = `pct_total...10`,
         outcomes_n = `n...11`,
         outcomes_n_change = `n_change...12`,
         outcomes_pct_change = `pct_change...13`,
         outcomes_pct_total = `pct_total...14`,
         LOS_n = `n...15`,
         LOS_n_change = `n_change...16`,
         LOS_pct_change = `pct_change...17`,
         LOS_pct_total = `pct_total...18`
         )

# inspect a few cases where funder migration is incomplete
wellcome_reg <- public_reg %>% filter(str_detect(funder, "Wellcome"))

apa_reg <- public_reg %>% filter(str_detect(funder, "American Psychological Association") | 
                                   str_detect(funder, "American Psychological Foundation") | 
                                   str_detect(funder, "American Psychology-Law Society") | 
                                   str_detect(funder, "Society for the Psychological Study of Social Issues"))

# correct funder name-ROR mapping provided by ENG
funder_map <- read_csv("~/Desktop/funder_mapping.csv", col_names = FALSE) %>%
  rename(funder_identifier = X1,
         new_funder = X2)

# create mapping of existing funder name-ROR-new funder name
mod_funders <- all_reg %>%
  select(reg_guid, funder, funder_identifier, funder_identifier_type) %>% distinct() %>% drop_na() %>%
  mutate(
    funder = map(funder, ~ fromJSON(.x)),
    funder_identifier = map(funder_identifier, ~ fromJSON(.x)),
    funder_identifier_type = map(funder_identifier_type, ~ fromJSON(.x))
  ) %>%
  unnest(c(funder, funder_identifier, funder_identifier_type)) %>%
  filter(funder_identifier_type == "ROR") %>%
  left_join(funder_map, by = "funder_identifier") %>%
  select(-reg_guid) %>% distinct()

# map new names to funder metrics
mod_funder_metrics <- funder_metrics %>%
  left_join(mod_funders, by = "funder") %>%
  filter(funder != new_funder) %>%
  select(funder, new_funder, everything())

# applying fix to funder_metadata ----
fm_original <- read_csv("~/Desktop/funder_metadata_2026-05-04.csv")

fm_original_funders <- fm_original %>%
  group_by(funder) %>%
  summarize(record_n = n())

fm_reconciled <- read_csv("~/Desktop/funder_metadata_reconciled_2026-05-09.csv")

fm_reconciled_funders <- fm_reconciled %>%
  group_by(funder) %>%
  summarize(record_n = n())