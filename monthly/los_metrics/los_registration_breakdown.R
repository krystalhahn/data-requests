library(readr)
library(tidyverse)
library(dplyr)
library(stringr)
library(googlesheets4)
library(tibble)
library(purrr)
library(tidyr)

# overall LOS registration metrics ----

# number of public registrations on the OSF
# number of registrations with (at least 1) outputs in the related resources (data, code, materials) sections
# number of registrations with at least 1 outcome linked in the related resource paper section
# number of registrations with both an output and outcome linked (LOS)

all_reg <- read_csv("~/Desktop/all_registry_reg_ext_2026-02-21.csv")

public_reg <- all_reg %>%
  filter(is_public, !is_deleted, !is.na(date_registered), moderation_state == "accepted", (spam_status != 2 | is.na(spam_status))) %>%
  # (retraction_state != "approved" | is.na(retraction_state))
  mutate(has_output = str_detect(connected_outputs, "DATA|CODE|MATERIALS|SUPPLEMENTS"),
         has_outcome = str_detect(connected_outputs, "PAPERS")) %>%
  mutate(is_los = has_output & has_outcome)

table(public_reg$has_output)
table(public_reg$has_outcome)
table(public_reg$is_los)

# breakdown by attribute ----

# affiliated institutions
table(public_reg$institution == "[]")

public_reg_inst <- public_reg %>%
  mutate(institution = str_extract_all(institution, "[^\\[\\]',]+")) %>%
  unnest(institution) %>%
  mutate(institution = str_trim(institution)) %>%
  count(institution, sort = TRUE)

# funder represented in metadata
table(is.na(public_reg$funder))

public_reg_funder <- public_reg %>%
  mutate(funder = str_extract_all(funder, "[^\\[\\]',]+")) %>%
  unnest(funder) %>%
  mutate(funder = str_trim(funder)) %>%
  count(funder, sort = TRUE)

# top-level subject
public_reg_subject <- public_reg %>%
  mutate(subject_parent = str_extract_all(subject_parent, "[^\\[\\]',]+")) %>%
  unnest(subject_parent) %>%
  mutate(subject_parent = str_trim(subject_parent)) %>%
  count(subject_parent, sort = TRUE)

# lower-level subject
public_reg_allsubject <- public_reg %>%
  mutate(subject = str_extract_all(subject, "[^\\[\\]',]+")) %>%
  unnest(subject) %>%
  mutate(subject = str_trim(subject)) %>%
  count(subject, sort = TRUE)

# registration template
view(table(public_reg$template))

# registration provider
view(table(public_reg$registry))
