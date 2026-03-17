library(readr)
library(tidyverse)
library(dplyr)
library(stringr)
library(googlesheets4)
library(tibble)
library(purrr)
library(tidyr)

all_reg <- read_csv("~/Desktop/all_registry_reg_ext_2026-02-21.csv")

public_reg <- all_reg %>%
  filter(is_public, !is_deleted, !is.na(date_registered), moderation_state == "accepted", (spam_status != 2 | is.na(spam_status))) %>%
  # (retraction_state != "approved" | is.na(retraction_state))
  mutate(has_output = str_detect(connected_outputs, "DATA|CODE|MATERIALS|SUPPLEMENTS"),
         has_outcome = str_detect(connected_outputs, "PAPERS")) %>%
  mutate(is_los = has_output & has_outcome)

# write to sheet ----
# set los_sheet_url variable

## Current attribute sheets ----
# not longitudinal

pct <- function(x) round(mean(x) * 100, 1)

### Overall ----
public_reg_overall <- public_reg %>%
  summarize(total = n(),
            LOS_n = sum(is_los),
            LOS_pct = pct(is_los),
            outputs_n = sum(has_output),
            outputs_pct = pct(has_output),
            outcomes_n = sum(has_outcome),
            outcomes_pct = pct(has_outcome))

write_sheet(public_reg_overall, los_sheet_url, "Overall")

### Affiliated ----

public_reg_affiliated <- public_reg %>%
  mutate(affiliated = map_chr(institution, ~ {
    if (is.na(.x)) return("Unaffiliated")
    result <- fromJSON(.x)
    if (length(result) == 0) "Unaffiliated" else "Affiliated"
  })) %>%
  group_by(affiliated) %>%
  summarize(total = n(),
            LOS_n = sum(is_los),
            LOS_pct = pct(is_los),
            outputs_n = sum(has_output),
            outputs_pct = pct(has_output),
            outcomes_n = sum(has_outcome),
            outcomes_pct = pct(has_outcome))

write_sheet(public_reg_affiliated, los_sheet_url, "Affiliated")

### Institution ----

public_reg_institution <- public_reg %>%
  mutate(institution = map(institution, ~ {
    if (is.na(.x)) return(NA_character_)
    result <- fromJSON(.x)
    if (length(result) == 0) NA_character_ else as.character(result)
  })) %>%
  unnest(institution) %>%
  mutate(institution = if_else(is.na(institution), "Unaffiliated", institution)) %>%
  group_by(institution) %>%
  summarize(total = n(),
            LOS_n = sum(is_los),
            LOS_pct = pct(is_los),
            outputs_n = sum(has_output),
            outputs_pct = pct(has_output),
            outcomes_n = sum(has_outcome),
            outcomes_pct = pct(has_outcome))

write_sheet(public_reg_institution, los_sheet_url, "Institution")

### Funded ----

public_reg_funded <- public_reg %>%
  mutate(funded = map_chr(funder, ~ {
    if (is.na(.x)) return("Unfunded")
    result <- fromJSON(.x)
    if (length(result) == 0) "Unfunded" else "Funded"
  })) %>%
  group_by(funded) %>%
  summarize(total = n(),
            LOS_n = sum(is_los),
            LOS_pct = pct(is_los),
            outputs_n = sum(has_output),
            outputs_pct = pct(has_output),
            outcomes_n = sum(has_outcome),
            outcomes_pct = pct(has_outcome))

write_sheet(public_reg_funded, los_sheet_url, "Funded")

### Funder ----

public_reg_funder <- public_reg %>%
  mutate(funder = map(funder, ~ {
    if (is.na(.x)) return(NA_character_)
    result <- fromJSON(.x)
    if (length(result) == 0) NA_character_ else as.character(result)
  })) %>%
  unnest(funder) %>%
  mutate(funder = if_else(is.na(funder), "Unfunded", funder)) %>%
  group_by(funder) %>%
  summarize(total = n(),
            LOS_n = sum(is_los),
            LOS_pct = pct(is_los),
            outputs_n = sum(has_output),
            outputs_pct = pct(has_output),
            outcomes_n = sum(has_outcome),
            outcomes_pct = pct(has_outcome))

write_sheet(public_reg_funder, los_sheet_url, "Funder")

### Template ----

dr_public_reg_template <- public_reg %>%
  group_by(template) %>%
  summarize(total = n(),
            LOS_n = sum(is_los),
            LOS_pct = pct(is_los),
            outputs_n = sum(has_output),
            outputs_pct = pct(has_output),
            outcomes_n = sum(has_outcome),
            outcomes_pct = pct(has_outcome))

write_sheet(public_reg_template, los_sheet_url, "Template")

### Registry ----

public_reg_registry <- public_reg %>%
  group_by(registry) %>%
  summarize(total = n(),
            LOS_n = sum(is_los),
            LOS_pct = pct(is_los),
            outputs_n = sum(has_output),
            outputs_pct = pct(has_output),
            outcomes_n = sum(has_outcome),
            outcomes_pct = pct(has_outcome))

write_sheet(public_reg_registry, los_sheet_url, "Registry")

### Top-level Subject ----

public_reg_subject_parent <- public_reg %>%
  mutate(subject_parent = map(subject_parent, ~ {
    if (is.na(.x)) return(NA_character_)
    result <- fromJSON(.x)
    if (length(result) == 0) NA_character_ else as.character(result)
  })) %>%
  unnest(subject_parent) %>%
  mutate(subject_parent = if_else(is.na(subject_parent), "No subject", subject_parent)) %>%
  group_by(subject_parent) %>%
  summarize(total = n(),
            LOS_n = sum(is_los),
            LOS_pct = pct(is_los),
            outputs_n = sum(has_output),
            outputs_pct = pct(has_output),
            outcomes_n = sum(has_outcome),
            outcomes_pct = pct(has_outcome))

write_sheet(public_reg_subject_parent, los_sheet_url, "Top-level Subject")

### Lower-level Subject ----
public_reg_subject <- public_reg %>%
  mutate(subject = map(subject, ~ {
    if (is.na(.x)) return(NA_character_)
    result <- fromJSON(.x)
    if (length(result) == 0) NA_character_ else as.character(result)
  })) %>%
  unnest(subject) %>%
  mutate(subject = if_else(is.na(subject), "No subject", subject)) %>%
  group_by(subject) %>%
  summarize(total = n(),
            LOS_n = sum(is_los),
            LOS_pct = pct(is_los),
            outputs_n = sum(has_output),
            outputs_pct = pct(has_output),
            outcomes_n = sum(has_outcome),
            outcomes_pct = pct(has_outcome))

write_sheet(public_reg_subject, los_sheet_url, "Lower-level subject")