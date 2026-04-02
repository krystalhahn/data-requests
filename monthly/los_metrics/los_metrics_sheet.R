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

# Addition of change metrics: Master sheet --> individual sheets ----

## generate current month's long data ----

current_month <- as.character(month(floor_date(Sys.Date(), "month") - months(1), label = TRUE, abbr = FALSE))
prev_month <- as.character(month(floor_date(Sys.Date(), "month") - months(2), label = TRUE, abbr = FALSE))

# helper functions for summarizing LOS metrics

# calculate proportion, but values will be formatted in sheet to appear as percentages
# round to 4 decimal points so when cells are selected, only two decimal points are shown
pct <- function(x) round(mean(x), 4)

# generate long format directly from raw data
summarize_long <- function(df, dimension_name, grouping_variables = character(0), ...) {
  
  df %>%
    group_by(across(all_of(grouping_variables)), ...) %>%
    summarize(
      total   = n(),
      outputs = sum(has_output),
      outcomes = sum(has_outcome),
      LOS     = sum(is_los),
      outputs_pct  = pct(has_output),
      outcomes_pct = pct(has_outcome),
      LOS_pct      = pct(is_los),
      .groups = "drop"
    ) %>%
    pivot_longer(
      cols = -any_of(grouping_variables),
      names_to = "metric",
      values_to = "value"
    ) %>%
    mutate(
      measure = case_when(
        str_detect(metric, "_pct$") ~ "pct_total",
        TRUE                        ~ "n"
      ),
      metric = str_remove(metric, "_pct$"),
      dimension = dimension_name
    ) %>%
    { if (length(grouping_variables) >= 1) rename(., attribute = all_of(grouping_variables[1])) else mutate(., attribute = NA) } %>%
    { if (length(grouping_variables) >= 2) rename(., attribute_2 = all_of(grouping_variables[2])) else mutate(., attribute_2 = NA) } %>%
    select(dimension, metric, measure, attribute, attribute_2, value)
}

# pull existing funders to determine new and existing funders below
existing_funders <- read_sheet(los_sheet_url, "Funder")

los_metrics_long <- bind_rows(
  
  # overall
  public_reg %>% summarize_long("overall"),
  
  # affiliated
  public_reg %>%
    mutate(attribute = map_chr(institution, ~ {
      if (is.na(.x)) return("Unaffiliated")
      result <- fromJSON(.x)
      if (length(result) == 0) "Unaffiliated" else "Affiliated"
    })) %>%
    summarize_long("affiliated", "attribute"),
  
  # institution
  public_reg %>%
    mutate(attribute = map(institution, ~ {
      if (is.na(.x)) return(NA_character_)
      result <- fromJSON(.x)
      if (length(result) == 0) NA_character_ else as.character(result)
    })) %>%
    unnest(attribute) %>%
    mutate(attribute = if_else(is.na(attribute), "Unaffiliated", attribute)) %>%
    summarize_long("institution", "attribute"),
  
  # funded
  public_reg %>%
    mutate(funder = map(funder, ~ {
      if (is.na(.x)) return(NA_character_)
      result <- fromJSON(.x)
      if (length(result) == 0) NA_character_ else as.character(result)
    })) %>%
    unnest(funder) %>%
    mutate(funder = if_else(is.na(funder), "Unfunded", funder)) %>%
    group_by(reg_guid) %>%
    summarize(
      is_new      = any(!funder %in% current_funders$funder & funder != "Unfunded"),
      is_existing = any(funder %in% current_funders$funder & funder != "Unfunded"),
      is_unfunded = all(funder == "Unfunded"),
      has_output  = first(has_output),
      has_outcome = first(has_outcome),
      is_los      = first(is_los),
      .groups = "drop"
    ) %>%
    mutate(attribute = case_when(
      is_unfunded  ~ "Unfunded",
      is_new       ~ "New funders",
      is_existing  ~ "Existing funders"
    )) %>%
    bind_rows(filter(., attribute != "Unfunded") %>% mutate(attribute = "Funded")) %>%
    (\(df) if (!"New funders" %in% df$attribute)
      bind_rows(df, tibble(attribute = "New funders", has_output = 0, has_outcome = 0, is_los = 0))
     else df)() %>%
    summarize_long("funded", "attribute"),
  
  # funder
  public_reg %>%
    mutate(attribute = map(funder, ~ {
      if (is.na(.x)) return(NA_character_)
      result <- fromJSON(.x)
      if (length(result) == 0) NA_character_ else as.character(result)
    })) %>%
    unnest(attribute) %>%
    mutate(attribute = if_else(is.na(attribute), "Unfunded", attribute),) %>%
    summarize_long("funder", "attribute"),
  
  # template
  public_reg %>%
    rename(attribute = template) %>%
    summarize_long("template", "attribute"),
  
  # registry
  public_reg %>%
    rename(attribute = registry) %>%
    summarize_long("registry", "attribute"),
  
  # template-registry pair
  public_reg %>%
    rename(attribute = template, attribute_2 = registry) %>%
    summarize_long("template-registry pair", c("attribute", "attribute_2")),
  
  # top-level subject
  public_reg %>%
    mutate(attribute = map(subject_parent, ~ {
      if (is.na(.x)) return(NA_character_)
      result <- fromJSON(.x)
      if (length(result) == 0) NA_character_ else as.character(result)
    })) %>%
    unnest(attribute) %>%
    mutate(attribute = if_else(is.na(attribute), "Unspecified", attribute)) %>%
    summarize_long("top-level subject", "attribute"),
  
  # lower-level subject
  public_reg %>%
    mutate(attribute = map(subject, ~ {
      if (is.na(.x)) return(NA_character_)
      result <- fromJSON(.x)
      if (length(result) == 0) NA_character_ else as.character(result)
    })) %>%
    unnest(attribute) %>%
    mutate(attribute = if_else(is.na(attribute), "Unspecified", attribute)) %>%
    left_join(subject_types %>% 
                select(subject, parent_subject) %>% 
                rename(attribute = subject, attribute_2 = parent_subject), 
              by = "attribute") %>%
    summarize_long("lower-level subject", c("attribute", "attribute_2"))
) %>%
  rename(!!current_month := value)

# check that all metrics have been calculated
table(is.na(los_metrics_long[[current_month]]))

### calculate change metrics (n_change, pct_change) ----
key_cols <- c("dimension", "metric", "measure", "attribute", "attribute_2")

current_master <- read_sheet(los_sheet_url, sheet = "Master",
                             col_types = "cccccnnnllllllllll") 

los_metrics_change <- los_metrics_long %>%
  left_join(
    current_master %>% select(all_of(key_cols), prev_value = all_of(!!prev_month)),
    by = key_cols
  ) %>%
  mutate(
    curr_value = as.numeric(.data[[current_month]]),
    prev_value = as.numeric(prev_value)
  )

# base rows
base <- los_metrics_change %>%
  transmute(dimension, metric, measure, attribute, attribute_2, value = curr_value)

# n_change rows
n_change <- los_metrics_change %>%
  filter(measure == "n") %>%
  mutate(value = if_else(measure == "n", curr_value - prev_value, NA_real_)) %>%
  transmute(dimension, metric, measure = "n_change", attribute, attribute_2, value)

# pct_change rows
pct_change <- los_metrics_change %>%
  filter(measure == "n") %>%
  mutate(value = case_when(
    is.na(prev_value) ~ NA_real_,
    prev_value == 0 & curr_value == 0 ~ 0,
    prev_value == 0 & curr_value != 0 ~ NA_real_,
    TRUE ~ round((curr_value - prev_value) / prev_value, 4)
  )) %>%
  transmute(dimension, metric, measure = "pct_change", attribute, attribute_2, value)

# build master data for current month
los_metrics_master <- bind_rows(base, n_change, pct_change) %>%
  rename(!!current_month := value)

# set order of metric and measure levels
metric_levels  <- c("total", "outputs", "outcomes", "LOS")
measure_levels <- c("n", "n_change", "pct_change", "pct_total")
dimension_levels <- c("overall", "affiliated", "institution", "funded", "funder", "template", "registry", "template-registry pair", "top-level subject", "lower-level subject")

### write to Master sheet ----
# current Master sheet pulled in before calculating change metrics

updated_master <- current_master %>%
  select(-!!current_month) %>%
  full_join(los_metrics_master, by = key_cols) %>%
  mutate(
    dimension = factor(dimension, levels = dimension_levels), 
    metric = factor(metric, levels = metric_levels),
    measure = factor(measure, levels = measure_levels)
  ) %>% 
  arrange(dimension, attribute, metric, measure) %>%
  select(all_of(key_cols), !!prev_month, !!current_month, everything())

write_sheet(updated_master, los_sheet_url, sheet = "Master")

## generate dimension data for individual dimension sheets ----

# define dimensions and their grouping attributes
dims <- list(
  list(name = "Overall",                 dim = "overall",                attr = NULL,                           attr1_name = NULL,   attr2_name = NULL),
  list(name = "Affiliated",              dim = "affiliated",             attr = "attribute",                    attr1_name = "affiliated_status", attr2_name = NULL),
  list(name = "Institution",             dim = "institution",            attr = "attribute",                    attr1_name = "institution", attr2_name = NULL),
  list(name = "Funded",                  dim = "funded",                 attr = "attribute",                    attr1_name = "funded_status", attr2_name = NULL),
  list(name = "Funder",                  dim = "funder",                 attr = "attribute",                    attr1_name = "funder", attr2_name = NULL),
  list(name = "Template",                dim = "template",               attr = "attribute",                    attr1_name = "template", attr2_name = NULL),
  list(name = "Registry",                dim = "registry",               attr = "attribute",                    attr1_name = "registry", attr2_name = NULL),
  list(name = "Template-Registry pair",  dim = "template-registry pair", attr = c("attribute", "attribute_2"),  attr1_name = "template", attr2_name = "registry"),
  list(name = "Top-level Subject",       dim = "top-level subject",      attr = "attribute",                    attr1_name = "subject", attr2_name = NULL),
  list(name = "Lower-level Subject",     dim = "lower-level subject",    attr = c("attribute", "attribute_2"),  attr1_name = "subject", attr2_name = "parent_subject")
)

# write wide data to each dimension sheet
walk(dims, ~ {
  
  id_cols <- .x$attr
  
  los_metrics_wide <- los_metrics_master %>%
    filter(dimension == .x$dim) %>%
    mutate(
      metric  = factor(metric, levels = metric_levels),
      measure = factor(measure, levels = measure_levels)
    ) %>%
    arrange(across(all_of(c(id_cols, "metric", "measure")))) %>%
    pivot_wider(
      id_cols = all_of(id_cols),
      names_from = c("metric", "measure"),
      values_from = !!current_month,
      names_glue = "{metric}_{measure}"
    ) %>%
    mutate(month = format(floor_date(Sys.Date(), "month") - months(1), "%Y-%m")) %>%
    select(month, everything())
  
  # rename attribute columns if new names are provided
  if (!is.null(.x$attr1_name)) {
    los_metrics_wide <- los_metrics_wide %>% rename(!!.x$attr1_name := !!sym(id_cols[1]))
  }
  if (!is.null(.x$attr2_name) && length(id_cols) == 2) {
    los_metrics_wide <- los_metrics_wide %>% rename(!!.x$attr2_name := !!sym(id_cols[2]))
  }
  
  write_sheet(los_metrics_wide, los_sheet_url, sheet = .x$name)
})

## adding yearly totals to Master tab ----
current_year = as.character(year(floor_date(Sys.Date(), "year")))
month_cols <- month.name
prev_dec_col <- paste("December", as.numeric(current_year) - 1)

updated_master_wtotals <- updated_master %>%
  rowwise() %>%
  mutate(
    latest_n = if_else(
      measure == "n",
      dplyr::last(na.omit(c_across(all_of(month_cols)))),
      NA_real_
    ),
    prev_dec_n = if_else(
      measure == "n",
      .data[[prev_dec_col]],
      NA_real_
    )
  ) %>%
  ungroup() %>%
  group_by(dimension, metric, attribute, attribute_2) %>%
  tidyr::fill(prev_dec_n, latest_n, .direction = "downup") %>%
  rowwise() %>%
  mutate(
    
    !!current_year := case_when(
      measure == "n"        ~ latest_n,
      measure == "n_change" ~ sum(c_across(all_of(month_cols)), na.rm = TRUE),
      measure == "pct_change" ~ {
        if (is.na(latest_n) || is.na(prev_dec_n) || prev_dec_n == 0) NA_real_
        else round((latest_n - prev_dec_n) / prev_dec_n, 4)
      },
      measure == "pct_total" ~ dplyr::last(na.omit(c_across(all_of(month_cols)))),
      TRUE ~ NA_real_
    )
  ) %>%
  ungroup() %>%
  select(-latest_n, -prev_dec_n)

write_sheet(updated_master_wtotals, los_sheet_url, sheet = "Master")

### adding funder_type to funder tab ----

existing_funders <- updated_master %>% 
  filter(dimension == "funder" & 
           metric == "total" &
           measure == "n" & 
           !is.na(.data[[prev_month]])) %>% 
  rename(funder = attribute) %>% distinct(funder)

public_reg_funder <- read_sheet(los_sheet_url, sheet = "Funder")

public_reg_funder_types <- public_reg_funder %>%
  mutate(
    funder_type = case_when(
      !funder %in% existing_funders$funder & funder != "Unfunded" ~ "new",
      funder %in% existing_funders$funder & funder != "Unfunded"  ~ "existing",
      funder == "Unfunded"                                           ~ "unfunded"
    )
  ) %>%
  select(month, funder, funder_type, everything())

write_sheet(public_reg_funder_types, los_sheet_url, sheet = "Funder")

## format sheet data ----
# specifically, use a batch update API request to format percentage values

los_sheet_id <- gs4_get(los_sheet_url)$spreadsheet_id

### individual dimension tabs ----

# build the list of tabs and _pct columns
los_sheet_props <- sheet_properties(los_sheet_url) %>%
  select(name, id)

# find the column indices of _pct columns in each tab
pct_cols <- map(1:nrow(los_sheet_props), ~ {
  tab_name <- los_sheet_props$name[.x]
  tab_id   <- los_sheet_props$id[.x]
  
  headers <- read_sheet(los_sheet_url, sheet = tab_name, n_max = 0) %>% names()
  
  pct_indices <- which(str_detect(headers, "_pct")) - 1
  
  col_ranges <- map(pct_indices, ~ c(.x, .x + 1))
  
  list(sheet_id = tab_id, col_ranges = col_ranges)
})

dimension_tab_requests <- map(pct_cols, ~ {
  tab <- .x
  map(tab$col_ranges, ~ list(
    repeatCell = list(
      range = list(sheetId = tab$sheet_id,
                   startColumnIndex = .x[1],
                   endColumnIndex = .x[2]),
      cell = list(userEnteredFormat = list(
        numberFormat = list(type = "PERCENT", pattern = "0.0%;-0.0%;0%")
      )),
      fields = "userEnteredFormat.numberFormat"
    )
  ))
}) %>%
  unlist(recursive = FALSE)

### Master tab ----

# read the Master sheet to find _pct row positions
master <- read_sheet(los_sheet_url, sheet = "test")
pct_rows <- which(str_detect(master$measure, "pct"))

master_sheet_id <- sheet_properties(los_sheet_url) %>%
  filter(name == "test") %>%
  pull(id)

# build requests targeting specific ("pct") rows in Master tab
master_tab_requests <- map(pct_rows, ~ list(
  repeatCell = list(
    range = list(
      sheetId = master_sheet_id,
      startRowIndex = .x,      # 0-indexed, so actual row number - 1
      endRowIndex = .x + 1,
      startColumnIndex = 5,    # first value column
      endColumnIndex = 100     # far enough to cover all month columns
    ),
    cell = list(userEnteredFormat = list(
      numberFormat = list(type = "PERCENT", pattern = "0.0%;-0.0%;0%")
    )),
    fields = "userEnteredFormat.numberFormat"
  )
))

req <- request_generate(
  endpoint = "sheets.spreadsheets.batchUpdate",
  params = list(
    spreadsheetId = los_sheet_id,
    requests = c(dimension_tab_requests, master_tab_requests)
  )
)

request_make(req)

# Pre-addition of change metrics: individual sheets --> Master sheet ----

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

### overall
public_reg_overall <- public_reg %>% summarize_metrics()

write_sheet(public_reg_overall, los_sheet_url, "Overall")

### affiliated

public_reg_affiliated <- public_reg %>%
  mutate(affiliated = map_chr(institution, ~ {
    if (is.na(.x)) return("Unaffiliated")
    result <- fromJSON(.x)
    if (length(result) == 0) "Unaffiliated" else "Affiliated"
  })) %>%
  summarize_metrics(affiliated)

write_sheet(public_reg_affiliated, los_sheet_url, "Affiliated")

### institution

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

### funded

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

### funder

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

### template

public_reg_template <- public_reg %>% summarize_metrics(template)

write_sheet(public_reg_template, los_sheet_url, "Template")

### registry

public_reg_registry <- public_reg %>% summarize_metrics(registry)

write_sheet(public_reg_registry, los_sheet_url, "Registry")

### template-registry pairs
public_reg_template_registry <- public_reg %>% summarize_metrics(template, registry)

write_sheet(public_reg_template_registry, los_sheet_url, "Template-Registry pair")

### top-level subject

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

### lower-level subject
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
