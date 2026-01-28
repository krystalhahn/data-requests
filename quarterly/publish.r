library(googledrive)
library(log4r)

options(googledrive_quiet = TRUE)


# Parameters -------------------------------------------------------------------
USER <- "alex@cos.io"
FILENAMES <- c(
  "all_domain_metrics.csv",
  "inst_active_users.csv",
  "inst_preprintprovider_metrics.csv",
  "institutional_metrics.csv",
  "regional_storage_metrics.csv",
  "top_inst_views_2025_q4.csv",
  "monthly_inst_views_2025_q4.csv"
)
QUARTERLY_FID <- "1Kxq7dKIx1L31jb6q6rL9znUzxVKOrc9q"
VERSION <- "2025-Q4"


# Run --------------------------------------------------------------------------
log <- create.logger(
  logfile = here::here("logs", "quarterly-publish.log"),
  level = "INFO"
)

info(log, "Publishing quarterly institutions data on Google Drive.")
drive_auth(email = USER, cache = FALSE)

info(log, glue::glue("\tChecking for {VERSION} subfolder"))
check <- drive_ls(
  path = as_id(QUARTERLY_FID),
  pattern = VERSION
)
if (nrow(check) > 0) {
  subdir_id <- check$id[1]
} else {
  info(log, glue::glue("\tFolder not found.  Creating {VERSION} subfolder."))
  new_folder <- drive_mkdir(
    path = as_id(QUARTERLY_FID),
    name = VERSION
  )
  subdir_id <- new_folder$id
}


for (filename in FILENAMES) {
  info(log, paste0("\tWriting ", filename, "."))

  drive_put(
    media = here::here("data", filename),
    path = as_id(subdir_id),
    name = filename
  )
  Sys.sleep(5) # To avoid rate limiting
}
info(log, "Publishing complete!\n\n")
