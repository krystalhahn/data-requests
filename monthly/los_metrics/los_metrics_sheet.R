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
            outputs_n = sum(has_output),
            outputs_pct = pct(has_output),
            outcomes_n = sum(has_outcome),
            outcomes_pct = pct(has_outcome),
            LOS_n = sum(is_los),
            LOS_pct = pct(is_los)) %>%
  mutate(across(ends_with("_pct"), ~ paste0(.x, "%"))) %>%
  mutate(across(where(is.numeric), as.character))

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
            outputs_n = sum(has_output),
            outputs_pct = pct(has_output),
            outcomes_n = sum(has_outcome),
            outcomes_pct = pct(has_outcome),
            LOS_n = sum(is_los),
            LOS_pct = pct(is_los)) %>%
  mutate(across(ends_with("_pct"), ~ paste0(.x, "%"))) %>%
  mutate(across(where(is.numeric), as.character))

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
            outputs_n = sum(has_output),
            outputs_pct = pct(has_output),
            outcomes_n = sum(has_outcome),
            outcomes_pct = pct(has_outcome),
            LOS_n = sum(is_los),
            LOS_pct = pct(is_los)) %>%
  mutate(across(ends_with("_pct"), ~ paste0(.x, "%"))) %>%
  mutate(across(where(is.numeric), as.character))

write_sheet(public_reg_institution, los_sheet_url, "Institution")

### Funded ----

current_funders <- read_sheet(los_sheet_url, "Funder")

public_reg_funded <- public_reg %>%
  mutate(funder = map(funder, ~ {
    if (is.na(.x)) return(NA_character_)
    result <- fromJSON(.x)
    if (length(result) == 0) NA_character_ else as.character(result)
  })) %>%
  unnest(funder) %>%
  mutate(funder = if_else(is.na(funder), "Unfunded", funder)) %>%
  group_by(reg_guid) %>%
  summarize(
    # a registration is "new" if ANY of its funders are new
    is_new = any(!funder %in% current_funders$funder & funder != "Unfunded"),
    is_existing = any(funder %in% current_funders$funder & funder != "Unfunded"),
    is_unfunded = all(funder == "Unfunded"),
    # carry through the metrics - take first value since they're the same per reg
    has_output = first(has_output),
    has_outcome = first(has_outcome),
    is_los = first(is_los)
  ) %>%
  mutate(funded = case_when(
    is_unfunded             ~ "Unfunded",
    is_new                  ~ "New funders",
    is_existing             ~ "Existing funders"
  )) %>%
  bind_rows(funded_classified %>% 
              filter(funded != "Unfunded") %>% 
              mutate(funded = "Funded")) %>%
  group_by(funded) %>%
  summarize(total = n(),
            outputs_n = sum(has_output),
            outputs_pct = pct(has_output),
            outcomes_n = sum(has_outcome),
            outcomes_pct = pct(has_outcome),
            LOS_n = sum(is_los),
            LOS_pct = pct(is_los)) %>%
  mutate(across(ends_with("_pct"), ~ paste0(.x, "%"))) %>%
  mutate(across(where(is.numeric), as.character)) %>%
  mutate(funded = factor(funded, levels = c("Funded", "New funders", "Existing funders", "Unfunded"))) %>%
  arrange(funded)

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
            outputs_n = sum(has_output),
            outputs_pct = pct(has_output),
            outcomes_n = sum(has_outcome),
            outcomes_pct = pct(has_outcome),
            LOS_n = sum(is_los),
            LOS_pct = pct(is_los)) %>%
  mutate(across(ends_with("_pct"), ~ paste0(.x, "%"))) %>%
  mutate(across(where(is.numeric), as.character)) %>%
  mutate(
    funder_type = case_when(
      !funder %in% current_funders$funder & funder != "Unfunded" ~ "new",
      funder %in% current_funders$funder & funder != "Unfunded" ~ "existing",
      funder == "Unfunded" ~ "unfunded"
    )) %>%
  select(funder, funder_type, everything())

write_sheet(public_reg_funder, los_sheet_url, "Funder")

### Template ----

public_reg_template <- public_reg %>%
  group_by(template) %>%
  summarize(total = n(),
            outputs_n = sum(has_output),
            outputs_pct = pct(has_output),
            outcomes_n = sum(has_outcome),
            outcomes_pct = pct(has_outcome),
            LOS_n = sum(is_los),
            LOS_pct = pct(is_los)) %>%
  mutate(across(ends_with("_pct"), ~ paste0(.x, "%"))) %>%
  mutate(across(where(is.numeric), as.character))

write_sheet(public_reg_template, los_sheet_url, "Template")

### Registry ----

public_reg_registry <- public_reg %>%
  group_by(registry) %>%
  summarize(total = n(),
            outputs_n = sum(has_output),
            outputs_pct = pct(has_output),
            outcomes_n = sum(has_outcome),
            outcomes_pct = pct(has_outcome),
            LOS_n = sum(is_los),
            LOS_pct = pct(is_los)) %>%
  mutate(across(ends_with("_pct"), ~ paste0(.x, "%"))) %>%
  mutate(across(where(is.numeric), as.character))

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
            outputs_n = sum(has_output),
            outputs_pct = pct(has_output),
            outcomes_n = sum(has_outcome),
            outcomes_pct = pct(has_outcome),
            LOS_n = sum(is_los),
            LOS_pct = pct(is_los)) %>%
  mutate(across(ends_with("_pct"), ~ paste0(.x, "%"))) %>%
  mutate(across(where(is.numeric), as.character))

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
            outputs_n = sum(has_output),
            outputs_pct = pct(has_output),
            outcomes_n = sum(has_outcome),
            outcomes_pct = pct(has_outcome),
            LOS_n = sum(is_los),
            LOS_pct = pct(is_los)) %>%
  mutate(across(ends_with("_pct"), ~ paste0(.x, "%"))) %>%
  mutate(across(where(is.numeric), as.character))

write_sheet(public_reg_subject, los_sheet_url, "Lower-level subject")

## Master sheet with longitudinal long data ----

### To create current month's Master sheet ----

public_reg_overall_long <- public_reg_overall %>%
  pivot_longer(cols = everything(),
               names_to = "metric",
               values_to = "value") %>%
  mutate(measure = case_when(str_detect(metric, "_n") ~ "count",
                             str_detect(metric, "_pct") ~ "percentage",
                             .default = NA),
         metric = str_remove(metric, "_(n|pct)$"),
         dimension = "overall",
         attribute = NA) %>%
  select(metric, dimension, measure, attribute, value)

public_reg_affiliated_long <- public_reg_affiliated %>%
  pivot_longer(cols = -"affiliated",
               names_to = "metric",
               values_to = "value") %>%
  mutate(measure = case_when(str_detect(metric, "_n") ~ "count",
                             str_detect(metric, "_pct") ~ "percentage",
                             metric == "total" ~ "count"),
         metric = str_remove(metric, "_(n|pct)$"),
         dimension = "affiliated") %>%
  rename(attribute = affiliated) %>%
  select(metric, dimension, measure, attribute, value)

public_reg_institution_long <- public_reg_institution %>%
  pivot_longer(cols = -"institution",
               names_to = "metric",
               values_to = "value") %>%
  mutate(measure = case_when(str_detect(metric, "_n") ~ "count",
                             str_detect(metric, "_pct") ~ "percentage",
                             metric == "total" ~ "count"),
         metric = str_remove(metric, "_(n|pct)$"),
         dimension = "institution") %>%
  rename(attribute = institution) %>%
  select(metric, dimension, measure, attribute, value)

public_reg_funded_long <- public_reg_funded %>%
  pivot_longer(cols = -"funded",
               names_to = "metric",
               values_to = "value") %>%
  mutate(measure = case_when(str_detect(metric, "_n") ~ "count",
                             str_detect(metric, "_pct") ~ "percentage",
                             metric == "total" ~ "count"),
         metric = str_remove(metric, "_(n|pct)$"),
         dimension = "funded") %>%
  rename(attribute = funded) %>%
  select(metric, dimension, attribute, value)

public_reg_funder_long <- public_reg_funder %>%
  pivot_longer(cols = -"funder",
               names_to = "metric",
               values_to = "value") %>%
  mutate(measure = case_when(str_detect(metric, "_n") ~ "count",
                             str_detect(metric, "_pct") ~ "percentage",
                             metric == "total" ~ "count"),
         metric = str_remove(metric, "_(n|pct)$"),
         dimension = "funder") %>%
  rename(attribute = funder) %>%
  select(metric, dimension, attribute, value)

public_reg_template_long <- public_reg_template %>%
  pivot_longer(cols = -"template",
               names_to = "metric",
               values_to = "value") %>%
  mutate(measure = case_when(str_detect(metric, "_n") ~ "count",
                             str_detect(metric, "_pct") ~ "percentage",
                             metric == "total" ~ "count"),
         metric = str_remove(metric, "_(n|pct)$"),
         dimension = "template") %>%
  rename(attribute = template) %>%
  select(metric, dimension, attribute, value)

public_reg_registry_long <- public_reg_registry %>%
  pivot_longer(cols = -"registry",
               names_to = "metric",
               values_to = "value") %>%
  mutate(measure = case_when(str_detect(metric, "_n") ~ "count",
                             str_detect(metric, "_pct") ~ "percentage",
                             metric == "total" ~ "count"),
         metric = str_remove(metric, "_(n|pct)$"),
         dimension = "registry") %>%
  rename(attribute = registry) %>%
  select(metric, dimension, attribute, value)

public_reg_subject_parent_long <- public_reg_subject_parent %>%
  pivot_longer(cols = -"subject_parent",
               names_to = "metric",
               values_to = "value") %>%
  mutate(measure = case_when(str_detect(metric, "_n") ~ "count",
                             str_detect(metric, "_pct") ~ "percentage",
                             metric == "total" ~ "count"),
         metric = str_remove(metric, "_(n|pct)$"),
         dimension = "top-level subject") %>%
  rename(attribute = subject_parent) %>% 
  select(metric, dimension, attribute, value)

public_reg_subject_long <- public_reg_subject %>%
  pivot_longer(cols = -"subject",
               names_to = "metric",
               values_to = "value") %>%
  mutate(measure = case_when(str_detect(metric, "_n") ~ "count",
                             str_detect(metric, "_pct") ~ "percentage",
                             metric == "total" ~ "count"),
         metric = str_remove(metric, "_(n|pct)$"),
         dimension = "lower-level subject") %>%
  rename(attribute = subject) %>%
  select(metric, dimension, attribute, value)

los_metrics_long <- bind_rows(
  public_reg_overall_long,
  public_reg_affiliated_long,
  public_reg_institution_long,
  public_reg_funded_long,
  public_reg_funder_long,
  public_reg_template_long,
  public_reg_registry_long,
  public_reg_subject_parent_long,
  public_reg_subject_long
)

write_sheet(los_metrics_long, los_sheet_url, sheet = "Master")

### To update sheet after initial creation with new month's metrics ----

current_sheet <- read_sheet(los_sheet_url, sheet = "Master")
next_col <- ncol(current_sheet) + 1

range_write(los_sheet_url, 
            data = as.data.frame(los_metrics_long$value), 
            sheet = "Master",
            range = cell_cols(next_col),
            col_names = TRUE)

# will modify to handle when there are new institutions, funders, etc.
