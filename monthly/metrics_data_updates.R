library(dplyr)
library(httr)
library(purrr)
library(tidyr)
library(jsonlite)
library(googlesheets4)
library(lubridate)

# Runtime settings
USER <- "alex@cos.io"
TESTING <- FALSE

# Parameters
SHEET_IDS <- list(
  prod = list(
    nodes = "1ti6iEgjvr-hXyMT5NwCNfAg-PJaczrMUX9sr6Cj6_kM",
    files = "1gOodKyhEhegXd0sTnc0IURq282wMgZgwAgoZS8brVUQ",
    users = "1qEhmANiAIcdavuugUNPKqVjijxvlihA99vIU9KuBhww",
    downloads = "1vs-yRamfmBo_dYs0LsTJ4JZoefPwArQvgA4N4YuTZ8w",
    preprints = "14K6dlo0G5-PA0W14d2DDg4ZHK8cG40JQ8XybQ9yWQYY"
  ),
  test = list(
    nodes = "1GWZEpq0PLP0rWcQp3-M2b_0V8XDxyrjKLQRepJySmG0",
    files = "1YX4dPaZ0DF-nPyz_jCa1Ha4uqsrXTIO8J2KrYA6vt3U",
    users = "lp6rahU8Rn38ZYPYRnzNLORmBZs_gmUVnvvK7orDys4",
    downloads = "1S69HeQWMvabU4Mv-CVeoxq6FWR7EEDJu2wOR81aYoG0",
    preprints = "1YbYjbA42ot-Lhsc-qykxasbOrn3InlB5PdLJm3aAc0k"
  )
)


# FUNCTIONS --------------------------------------------------------------------
#' Append if sheet does not exist
smart_append <- function(tbl, ss, sheetname = "Sheet1") {
  safe_gs4_get <- purrr::safely(gs4_get)

  test <- safe_gs4_get(ss)

  if (is.null(test$result)) {
    sheet_write(ss, tbl, sheet = sheetname) # sheet does not exist
  } else {
    cloud_tbl <- read_sheet(ss) # sheet exists
    if (nrow(cloud_tbl) == 0) {
      sheet_write(tbl, ss, sheet = sheetname) # sheet is empty
    } else {
      sheet_append(tbl, ss, sheet = sheetname)
    }
  }
}


# function to create osf calls
metrics_extraction_call <- function(event_collection) {
  output <- GET(paste0(
    "https://api.osf.io/_/metrics/reports/",
    event_collection,
    "/recent/?start_date=",
    floor_date(Sys.Date(), "month") - months(1),
    "&end_date=",
    floor_date(Sys.Date(), "month") - days(1)
  ))
  return(output)
}

# function to clean API response calls
clean_api_response <- function(api_output) {
  cleaned_result <- fromJSON(prettify(api_output))$data |>
    # handle nested dataframes in created from json output
    map_if(is.data.frame, list) |>
    as_tibble() |>
    unnest(attributes) |>
    # handle if keen accidentally ran more than once in a night
    arrange(report_date) |>
    group_by(timestamp) |>
    slice(1L) |>
    ungroup() |>
    # make report_date a datetime
    mutate(report_date = paste0(report_date, "T00:00:00.000Z"))

  return(cleaned_result)
}


# MAIN --------------------------------------------------------------------
### Authorization ----
gs4_auth(email = USER, cache = FALSE)

### Make and store api calls ----
nodesummary_output <- metrics_extraction_call("node_summary")
filesummary_output <- metrics_extraction_call("osfstorage_file_count")
usersummary_output <- metrics_extraction_call("user_summary")
download_output <- metrics_extraction_call("download_count")
preprint_output <- metrics_extraction_call("preprint_summary")

### clean API results and make sure new df names and order match existing gsheets ----

node_data <- clean_api_response(nodesummary_output) |>
  # unnest variables
  unnest(c(nodes, registered_projects, projects), names_sep = ".") |>
  # rename to match existing column names
  rename(
    keen.timestamp = report_date,
    keen.created_at = timestamp
  ) |>
  # make sure column order correct
  dplyr::select(
    keen.created_at,
    keen.timestamp,
    projects.public,
    registered_projects.total,
    registered_projects.withdrawn,
    registered_projects.embargoed_v2
  )

file_data <- clean_api_response(filesummary_output) |>
  unnest(c(files), names_sep = ".") |>
  # rename to match existing column names
  rename(
    keen.timestamp = report_date,
    keen.created_at = timestamp,
    osfstorage_files_including_quickfiles.total = files.total,
    osfstorage_files_including_quickfiles.public = files.public
  ) |>
  # make sure column order correct
  dplyr::select(
    keen.timestamp,
    keen.created_at,
    osfstorage_files_including_quickfiles.public,
    osfstorage_files_including_quickfiles.total
  )

user_data <- clean_api_response(usersummary_output) |>
  # rename to match existing column names
  rename(
    keen.timestamp = report_date,
    keen.created_at = timestamp,
    status.active = active
  ) |>
  # make sure column order correct
  dplyr::select(keen.created_at, keen.timestamp, status.active)

download_data <- clean_api_response(download_output) |>
  # rename to match existing column names
  rename(
    keen.timestamp = report_date,
    keen.created_at = timestamp,
    files.total = daily_file_downloads
  ) |>
  # make sure column order correct
  dplyr::select(keen.timestamp, keen.created_at, files.total)

# can't use function for preprint data b/c need to handling groupings differently
preprint_data <- fromJSON(prettify(preprint_output))$data |>
  # handle nested dataframes in created from json output
  map_if(is.data.frame, list) |>
  as_tibble() |>
  unnest(attributes) |>
  # handle if keen accidentally ran more than once in a night
  arrange(report_date) |>
  group_by(timestamp, provider_key) |>
  slice(1L) |>
  ungroup() |>
  mutate(report_date = paste0(report_date, "T00:00:00.000Z")) |>
  # rename to match existing column names
  rename(
    keen.timestamp = report_date,
    keen.created_at = timestamp,
    provider.name = provider_key,
    provider.total = preprint_count
  ) |>
  # make sure column order correct
  dplyr::select(keen.created_at, keen.timestamp, provider.name, provider.total)

# remap provider name values to longform
pp_shortnames <- c(
  "africarxiv",
  "agrixiv",
  "arabixiv",
  "biohackrxiv",
  "bodoarxiv",
  "eartharxiv",
  "ecoevorxiv",
  "ecsarxiv",
  "edarxiv",
  "engrxiv",
  "focusarchive",
  "frenxiv",
  "inarxiv",
  "indiarxiv",
  "lawarxiv",
  "lissa",
  "livedata",
  "marxiv",
  "mediarxiv",
  "metaarxiv",
  "mindrxiv",
  "nutrixiv",
  "osf",
  "paleorxiv",
  "psyarxiv",
  "socarxiv",
  "sportrxiv",
  "thesiscommons"
)
pp_longnames <- c(
  "AfricArXiv",
  "AgriXiv",
  "Arabixiv",
  "BioHackrXiv",
  "BodoArXiv",
  "EarthArXiv",
  "EcoEvoRxiv",
  "ECSarXiv",
  "EdArXiv",
  "engrXiv",
  "FocUS Archive",
  "Frenxiv",
  "INA-Rxiv",
  "IndiaRxiv",
  "LawArXiv",
  "LIS Scholarship Archive",
  "Research AZ",
  "MarXiv",
  "MediArXiv",
  "MetaArXiv",
  "MindRxiv",
  "NutriXiv",
  "Open Science Framework",
  "PaleorXiv",
  "PsyArXiv",
  "SocArXiv",
  "SportRxiv",
  "Thesis Commons"
)
preprint_data$provider.name <- plyr::mapvalues(
  preprint_data$provider.name,
  from = pp_shortnames,
  to = pp_longnames
)

## existing sheet IDs (prod data sheets)
if (TESTING) {
  sheet_ids <- SHEET_IDS$test
} else {
  sheet_ids <- SHEET_IDS$prod
}
nodes_gdrive_file <- sheet_ids$nodes
files_grdrive_file <- sheet_ids$files
user_gdrive_file <- sheet_ids$users
download_gdrive_file <- sheet_ids$downloads
preprint_gdrive_file <- sheet_ids$preprints

## append new data to googlesheet
smart_append(node_data, ss = nodes_gdrive_file)
smart_append(file_data, ss = files_grdrive_file)
smart_append(user_data, ss = user_gdrive_file)
smart_append(download_data, ss = download_gdrive_file)
smart_append(preprint_data, ss = preprint_gdrive_file)

## calculating monthly numbers ----

# calculate start and end of needed range
end_2_month <- floor_date(now("utc"), "month") - months(1) - days(1)
end_last_month <- floor_date(now("utc"), "month") - days(1)

# set up function to return only needed rows for each sheet
startend_dates <- function(gsheet) {
  # retain only needed rows for calculations
  startend_sheet <- read_sheet(gsheet) |>
    mutate(keen.timestamp = ymd_hms(keen.timestamp)) |>
    filter(keen.timestamp == end_last_month | keen.timestamp == end_2_month)

  # return resulting sheet
  return(startend_sheet)
}

nodes_startend <- startend_dates(nodes_gdrive_file)
files_startend <- startend_dates(files_grdrive_file)
users_startend <- startend_dates(user_gdrive_file)

# additional process for pps to collapse across providers
preprints_startend <- startend_dates(preprint_gdrive_file) |>
  group_by(keen.timestamp) |>
  summarize(total_pps = sum(provider.total))

#### calculate monthly downloads ----
# downloads are a sum rather than a difference
read_sheet(download_gdrive_file, col_types = "??i") |>
  filter(
    keen.timestamp >= floor_date(now("utc"), "month") - months(1) &
      keen.timestamp < floor_date(now("utc"), "month")
  ) |>
  summarize(total = sum(files.total))

#### calculate monthly values ----
nodes_startend[2, "projects.public"] - nodes_startend[1, "projects.public"]
nodes_startend[2, "registered_projects.total"] -
  nodes_startend[1, "registered_projects.total"]

files_startend[2, "osfstorage_files_including_quickfiles.public"] -
  files_startend[1, "osfstorage_files_including_quickfiles.public"]
files_startend[2, "osfstorage_files_including_quickfiles.total"] -
  files_startend[1, "osfstorage_files_including_quickfiles.total"]

users_startend[2, "status.active"] - users_startend[1, "status.active"]

preprints_startend[2, "total_pps"] - preprints_startend[1, "total_pps"]
