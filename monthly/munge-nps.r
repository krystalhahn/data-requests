#!/usr/local/bin/Rscript --vanilla
source(here::here(".Rprofile"))


# Load functions and capture arguments
source(here::here("monthly", "R", "functions.r"))


ARGS <- commandArgs(trailingOnly = TRUE)
#1: input path for NPS user CSV
#2: input path for NPS institution CSV
#3 cutoff date (YYYY-MM-DD) to filter confirmed users

print(ARGS)

# Execute if script is run directly
if (sys.nframe() == 0) {
  library(log4r)
  NPS_MERGED_PATH = "data/nps-merged.csv"
  NPS_LOS_PATH = "data/nps-classified.csv"

  log <- create.logger(
    logfile = here::here("logs", "monthly-nps-munge.log"),
    level = "INFO"
  )
  info(log, "Starting NPS data munging process.")
  info(log, "\tMerging monthly NPS user and institution data.")
  tbl <- merge_nps_users_insts(
    nps_users_path = ARGS[1],
    nps_insts_path = ARGS[2],
    show_col_types = FALSE
  )
  readr::write_csv(tbl, NPS_MERGED_PATH, na = "")

  info(log, "\tClassifying NPS users in to LOS categories")
  classify_users(tbl, cutoff_date = ARGS[3]) |>
    readr::write_csv(NPS_LOS_PATH, na = "")

  log4r::info(log, glue::glue("\tMunging complete!\n\n"))
}
