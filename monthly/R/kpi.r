# Constants --------------------------------------------------------------------
ENDPOINTS <- c(
  "node_summary",
  "osfstorage_file_count",
  "user_summary",
  "download_count",
  "preprint_summary"
)

PREPRINT_PROVIDERS <- data.frame(
  shortnames = c(
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
  ),
  longnames = c(
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
)

API_RENAMES <- c(
  "keen.timestamp" = "report_date",
  "keen.created_at" = "timestamp",
  "files.total" = "osfstorage_files_including_quickfiles.total",
  "files.public" = "osfstorage_files_including_quickfiles.public",
  "active" = "status.active",
  "files.total" = "daily_file_downloads",
  "provider.name" = "provider_key",
  "provider.total" = "preprint_count"
)


KEEPVARS <- list(
  node_summary = rlang::exprs(
    keen.created_at,
    keen.timestamp,
    projects.public,
    registered_projects.total,
    registered_projects.withdrawn,
    registered_projects.embargoed_v2
  ),
  osfstorage_file_count = rlang::exprs(
    keen.timestamp,
    keen.created_at,
    osfstorage_files_including_quickfiles.public,
    osfstorage_files_including_quickfiles.total
  ),
  usersummary = rlang::exprs(
    keen.created_at,
    keen.timestamp,
    status.active
  ),
  download_count = rlang::exprs(
    keen.timestamp,
    keen.created_at,
    files.total
  ),
  preprint_summary = rlang::exprs(
    keen.created_at,
    keen.timestamp,
    provider.name,
    provider.total
  )
)

# Locations --------------------------------------------------------------------
GIDS <- list(
  prod = c(
    "node_summary" = "1ti6iEgjvr-hXyMT5NwCNfAg-PJaczrMUX9sr6Cj6_kM",
    "osfstorage_file_count" = "1gOodKyhEhegXd0sTnc0IURq282wMgZgwAgoZS8brVUQ",
    "user_summary" = "1qEhmANiAIcdavuugUNPKqVjijxvlihA99vIU9KuBhww",
    "download_count" = "1vs-yRamfmBo_dYs0LsTJ4JZoefPwArQvgA4N4YuTZ8w",
    "preprint_summary" = "14K6dlo0G5-PA0W14d2DDg4ZHK8cG40JQ8XybQ9yWQYY"
  )
)


# Functions --------------------------------------------------------------------
metrics_extraction_call <- function(event_collection, sleep = 0) {
  output <- httr::GET(paste0(
    "https://api.osf.io/_/metrics/reports/",
    event_collection,
    "/recent/?start_date=",
    lubridate::floor_date(Sys.Date(), "month") - months(1),
    "&end_date=",
    lubridate::floor_date(Sys.Date(), "month") - days(1)
  ))

  Sys.sleep(sleep)
  return(output)
}

clean_api_response <- function(api_output) {
  cleaned_result <- jsonlite::fromJSON(prettify(api_output))$data |>
    # handle nested dataframes in created from json output
    purrr::map_if(is.data.frame, list) |>
    tibble::as_tibble() |>
    tidyr::unnest(attributes) |>
    # handle if keen accidentally ran more than once in a night
    dplyr::arrange(report_date) |>
    dplyr::group_by(timestamp) |>
    dplyr::slice(1L) |>
    dplyr::ungroup() |>
    # make report_date a datetime
    dplyr::mutate(report_date = paste0(report_date, "T00:00:00.000Z"))

  return(cleaned_result)
}
