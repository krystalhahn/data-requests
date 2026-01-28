library(googledrive)
library(log4r)

USER <- "alex@cos.io"
NPS_PATH <- "data/nps-merged.csv"
NPS_FID <- "1a6d4UfGNpaELSkctBLvbSYXm2MfiN4sR"

log <- create.logger(
  logfile = here::here("logs", "monthly-publish.log"),
  level = "INFO"
)
info(log, "Publishing metrics data on Google Drive.")
drive_auth(email = USER, cache = FALSE)

info(log, "\tWriting NPS user data.")
drive_put(
  media = NPS_PATH,
  path = as_id(NPS_FID),
  name = "2026-01.csv"
)
info(log, "\tPublishing complete!\n\n")
