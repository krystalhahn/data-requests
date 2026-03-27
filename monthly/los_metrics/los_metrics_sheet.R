library(readr)
library(tidyverse)
library(dplyr)
library(stringr)
library(googlesheets4)
library(tibble)
library(purrr)
library(tidyr)

all_reg <- read_csv("~/Desktop/all_registrations_for_los_2026-03-04.csv")

public_reg <- all_reg %>%
  filter(is_public, !is_deleted, !is.na(date_registered), moderation_state == "accepted", (spam_status != 2 | is.na(spam_status))) %>%
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
              .groups = "drop")
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
    bind_rows(tibble(funded = "New funders", total = 0, 
                     outputs_n = 0, outputs_pct = 0, 
                     outcomes_n = 0, outcomes_pct = 0,
                     LOS_n = 0, LOS_pct = 0)) %>%
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
  mutate(subject_parent = if_else(is.na(subject_parent), "Unspecified", subject_parent)) %>%
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
  mutate(subject = if_else(is.na(subject), "Unspecified", subject)) %>%
  summarize_metrics(subject)

write_sheet(public_reg_subject, los_sheet_url, "Lower-level Subject")

# Format sheet data ----
# specifically, use a batch update API request to format percentage values

los_sheet_id <- gs4_get(los_sheet_url)$spreadsheet_id

# build the list of tabs and _pct columns
los_sheet_props <- sheet_properties(los_sheet_url) %>%
  select(name, id)

# find the column indices of _pct columns in each tab
tab_config <- map(1:nrow(los_sheet_props), ~ {
  tab_name <- los_sheet_props$name[.x]
  tab_id   <- los_sheet_props$id[.x]
  
  headers <- read_sheet(los_sheet_url, sheet = tab_name, n_max = 0) %>% names()
  
  pct_indices <- which(str_detect(headers, "_pct$")) - 1
  
  col_ranges <- map(pct_indices, ~ c(.x, .x + 1))
  
  list(sheet_id = tab_id, col_ranges = col_ranges)
})

requests <- map(tab_config, ~ {
  tab <- .x
  map(tab$col_ranges, ~ list(
    repeatCell = list(
      range = list(sheetId = tab$sheet_id,
                   startColumnIndex = .x[1],
                   endColumnIndex = .x[2]),
      cell = list(userEnteredFormat = list(
        numberFormat = list(type = "NUMBER", pattern = "0.0\"%\";0.0\"%\";0\"%\"")
      )),
      fields = "userEnteredFormat.numberFormat"
    )
  ))
}) %>%
  unlist(recursive = FALSE)

req <- request_generate(
  endpoint = "sheets.spreadsheets.batchUpdate",
  params = list(
    spreadsheetId = los_sheet_id,
    requests = requests
  )
)

request_make(req)

## Master sheet with longitudinal long data ----

### To create current month's Master sheet ----

# helper function for reshaping data for longitudinal dataset
reshape_data <- function(df, dimension_name, grouping_variables = character(0)) {
  df %>%
    pivot_longer(cols = -any_of(grouping_variables),
                 names_to = "metric",
                 values_to = "value") %>%
    { if (length(grouping_variables) >= 1) rename(., attribute = all_of(grouping_variables[1])) else . } %>%
    { if (length(grouping_variables) >= 2) rename(., additional_attribute = all_of(grouping_variables[2])) else . } %>%
    mutate(measure = case_when(str_detect(metric, "_n$")   ~ "count",
                               str_detect(metric, "_pct$") ~ "percentage",
                               metric == "total"           ~ "count",
                               .default = NA),
           metric = str_remove(metric, "_(n|pct)$"),
           dimension = dimension_name,
           attribute = if ("attribute" %in% names(.)) attribute else NA,
           additional_attribute = if ("additional_attribute" %in% names(.)) additional_attribute else NA) %>%
    select(dimension, metric, measure, attribute, additional_attribute, value)
}

public_reg_overall_long <- public_reg_overall %>% reshape_data("overall")

public_reg_affiliated_long <- public_reg_affiliated %>% reshape_data("affiliated", "affiliated")

public_reg_institution_long <- public_reg_institution %>% reshape_data("institution", "institution")

public_reg_funded_long <- public_reg_funded %>% reshape_data("funded", "funded")

public_reg_funder_long <- public_reg_funder %>% reshape_data("funder", c("funder", "funder_type"))

public_reg_template_long <- public_reg_template %>% reshape_data("template", "template")

public_reg_registry_long <- public_reg_registry %>% reshape_data("registry", "registry")

public_reg_template_registry_long <- public_reg_template_registry %>% reshape_data("template-registry pair", c("template", "registry"))

public_reg_subject_parent_long <- public_reg_subject_parent %>% reshape_data("top-level subject", "subject_parent")

public_reg_subject_long <- public_reg_subject %>% reshape_data("lower-level subject", "subject")

los_metrics_long <- bind_rows(
  public_reg_overall_long,
  public_reg_affiliated_long,
  public_reg_institution_long,
  public_reg_funded_long,
  public_reg_funder_long,
  public_reg_template_long,
  public_reg_registry_long,
  public_reg_template_registry_long,
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
