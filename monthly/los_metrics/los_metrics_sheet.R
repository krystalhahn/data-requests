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

# helper function for summarizing LOS metrics
pct <- function(x) round(mean(x) * 100, 1)

summarize_metrics <- function(df, ...) {
  df %>%
    group_by(...) %>%
    summarize(total = n(),
              outputs_n = sum(has_output),
              outputs_pct = pct(has_output),
              outcomes_n = sum(has_outcome),
              outcomes_pct = pct(has_outcome),
              LOS_n = sum(is_los),
              LOS_pct = pct(is_los),
              .groups = "drop") %>%
    mutate(across(ends_with("_pct"), ~ paste0(.x, "%"))) %>%
    mutate(across(where(is.numeric), as.character))
}

### Overall ----
public_reg_overall <- public_reg %>% summarize_metrics()

write_sheet(public_reg_overall, los_sheet_url, "Overall")

### Affiliated ----

public_reg_affiliated <- public_reg %>%
  mutate(affiliated = map_chr(institution, ~ {
    if (is.na(.x)) return("Unaffiliated")
    result <- fromJSON(.x)
    if (length(result) == 0) "Unaffiliated" else "Affiliated"
  })) %>%
  summarize_metrics(affiliated)

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
  summarize_metrics(institution)

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
  bind_rows(filter(., funded != "Unfunded") %>% 
              mutate(funded = "Funded")) %>%
  summarize_metrics(funded) %>%
  mutate(funded = factor(funded, levels = c("Funded", "New funders", "Existing funders", "Unfunded"))) %>%
  arrange(funded)

# if there are no new funders in the current month

if (!"New funders" %in% public_reg_funded$funded) {
  public_reg_funded <- public_reg_funded %>%
    bind_rows(tibble(funded = "New funders", total = "0", outputs_n = "0",
                     outputs_pct = "0%", outcomes_n = "0", outcomes_pct = "0%",
                     LOS_n = "0", LOS_pct = "0%")) %>%
    mutate(funded = factor(funded, levels = c("Funded", "New funders", "Existing funders", "Unfunded"))) %>%
    arrange(funded)
}

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
  summarize_metrics(funder) %>%
  mutate(
    funder_type = case_when(
      !funder %in% current_funders$funder & funder != "Unfunded" ~ "new",
      funder %in% current_funders$funder & funder != "Unfunded" ~ "existing",
      funder == "Unfunded" ~ "unfunded"
    )) %>%
  select(funder, funder_type, everything())

write_sheet(public_reg_funder, los_sheet_url, "Funder")

### Template ----

public_reg_template <- public_reg %>% summarize_metrics(template)

write_sheet(public_reg_template, los_sheet_url, "Template")

### Registry ----

public_reg_registry <- public_reg %>% summarize_metrics(registry)

write_sheet(public_reg_registry, los_sheet_url, "Registry")


### Template-Registry pairs ----
public_reg_template_registry <- public_reg %>% summarize_metrics(template, registry)

write_sheet(public_reg_template_registry, los_sheet_url, "Template-Registry pair")

### Top-level Subject ----

public_reg_subject_parent <- public_reg %>%
  mutate(subject_parent = map(subject_parent, ~ {
    if (is.na(.x)) return(NA_character_)
    result <- fromJSON(.x)
    if (length(result) == 0) NA_character_ else as.character(result)
  })) %>%
  unnest(subject_parent) %>%
  mutate(subject_parent = if_else(is.na(subject_parent), "No subject", subject_parent)) %>%
  summarize_metrics(subject_parent)

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
  summarize_metrics(subject)

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
  select(dimension, metric, measure, attribute, value)

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
  select(dimension, metric, measure, attribute, value)

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
  select(dimension, metric, measure, attribute, value)

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
  select(dimension, metric, measure, attribute, value)

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
  select(dimension, metric, measure, attribute, value)

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
  select(dimension, metric, measure, attribute, value)

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
  select(dimension, metric, measure, attribute, value)

public_reg_template_registry_long <- public_reg_template_registry %>%
  pivot_longer(cols = -c("template", "registry"),
               names_to = "metric",
               values_to = "value") %>%
  mutate(measure = case_when(str_detect(metric, "_n") ~ "count",
                             str_detect(metric, "_pct") ~ "percentage",
                             metric == "total" ~ "count"),
         metric = str_remove(metric, "_(n|pct)$"),
         dimension = "template-registry pair") %>%
  rename(attribute = template,
         additional_attribute = registry) %>%
  select(dimension, metric, measure, attribute, additional_attribute, value)

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
  select(dimension, metric, measure, attribute, value)

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
  select(dimension, metric, measure, attribute, value)

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
