library(readr)
library(tidyverse)
library(dplyr)
library(stringr)
library(googlesheets4)
library(tibble)
library(purrr)
library(tidyr)

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
  filter(funder != new_funder) %>%
  distinct(funder_identifier, funder, new_funder)
