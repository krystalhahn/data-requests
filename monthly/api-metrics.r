library(dplyr)
library(googlesheets4)
library(log4r)
library(lubridate)
library(jsonlite)
library(purrr)
library(tidyr)

# Parameters
USER <- "alex@cos.io"

# Load functions
source(here::here("monthly", "R", "kpi.r"))


# API Calls --------------------------------------------------------------------
api_data <- map(ENDPOINTS, metrics_extraction_call, sleep = 2) |>
  set_names(ENDPOINTS)


# Clean API Responses ----------------------------------------------------------
# Global cleaning
clean_data <- map(api_data, clean_api_response)

# Endpoint-specific cleaning
clean_data[["node_summary"]] <- clean_data$node_summary |>
  unnest(c(nodes, registered_projects, projects), names_sep = ".") |>
  rename(!!!API_RENAMES[API_RENAMES %in% names(clean_data$node_summary)]) |>
  select(!!!KEEPVARS$node_summary)

clean_data[["osfstorage_file_count"]] <- clean_data$osfstorage_file_count |>
  unnest(c(files), names_sep = ".") |>
  rename(
    !!!API_RENAMES[API_RENAMES %in% names(clean_data$osfstorage_file_count)]
  ) |>
  select(!!!KEEPVARS$osfstorage_file_count)

clean_data[["user_summary"]] <- clean_data$user_summary #|>
# rename(!!!API_RENAMES[API_RENAMES %in% names(clean_data$user_summary)]) |>
# select(!!!KEEPVARS$user_summary)

clean_data[["download_count"]] <- clean_data$download_count |>
  rename(!!!API_RENAMES[API_RENAMES %in% names(clean_data$download_count)]) |>
  select(!!!KEEPVARS$user_summary)

clean_data[["preprint_summary"]] <-
  fromJSON(prettify(api_data$preprint_summary))$data |>
  map_if(is.data.frame, list) |>
  as_tibble() |>
  unnest(attributes) |>
  arrange(report_date) |>
  group_by(timestamp, provider_key) |>
  slice(1L) |>
  ungroup() |>
  mutate(
    report_date = paste0(report_date, "T00:00:00.000Z"),
    provider_key = stringr::str_replace_all(
      provider_key,
      set_names(PREPRINT_PROVIDERS$longnames, PREPRINT_PROVIDERS$shortnames)
    )
  ) |>
  rename(!!!API_RENAMES[API_RENAMES %in% names(clean_data$preprint_summary)]) |>
  select(!!!KEEPVARS$preprint_summary)


# Append Data to Google Sheets -----------------------------------------------
# Authenticate
gs4_auth(
  email = USER,
  cache = ".secrets",
  use_oob = TRUE
)

# Append
walk(
  ENDPOINTS,
  ~ sheet_append(
    clean_data[[.x]],
    ss = GIDS$prod[[.x]]
  )
)


# Calculate Monthly Numbers ----------------------------------------------------

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
