library(readr)
library(tidyverse)
library(dplyr)
library(stringr)
library(googlesheets4)
library(tibble)
library(purrr)
library(tidyr)
gs4_auth(email = "krystal@cos.io", cache = FALSE)

# training dates and topics
trainings_url <- "https://docs.google.com/spreadsheets/d/1GK8ohtiZ2ML2mBFgIRe9qpBTzN3qNjktJOtgAkOFdI8/edit?gid=841413380#gid=841413380"
trainings <- read_sheet(trainings_url, sheet="dates_topics")

# one row per training group (collapses across multiple trainings per group)
dates <- trainings %>%
  select(inst, first_training_date, last_training_date, postsurvey_date) %>%
  distinct()

# training participant data ----

## AREN Pilot ----
# survey data
aren_pre <- read_csv('~/Desktop/trainings_los/AREN_Pilot_Pre-Survey.csv')[-c(1, 2), ]
aren_post <- read_csv('~/Desktop/trainings_los/AREN_Pilot_Post-Survey.csv')[-c(1, 2), ]
aren_osf <- aren_pre %>% select(RecipientEmail, osf, orcid, gscholar) %>%
  rename(osf_profile = osf, 
         orcid_profile = orcid) %>%
  mutate(osf_guid = str_extract(osf_profile, "(?<=/)[A-Za-z0-9]{5}(?=/?$)"),
         orcid = str_extract(orcid_profile, "\\d{4}-\\d{4}-\\d{4}-\\d{3}[\\dX]"))

# participant list (no-shows are possible, but they have access to the video)
aren_list <- read_csv('~/Desktop/trainings_los/AREN_Pilot_email_list.csv') %>% 
  mutate(inst = 'AREN') %>%
  select(-Language, -ExternalDataReference, -Phone) %>%
  left_join(aren_osf, by = join_by(Email == RecipientEmail)) %>%
  # only make FullName NA if both first and last are NA and don't include NA if only one name is present
  mutate(FullName = if_else(is.na(FirstName) & is.na(LastName), 
                            NA_character_, 
                            paste(FirstName, LastName, sep = " ") %>% 
                              trimws())) %>%
  left_join(dates, by = "inst")

## Round 2 Pilot ----
# survey data
round2_pre <-read_csv('~/Desktop/trainings_los/Training_Pre-Survey_Round2_Pilot.csv')[-c(1, 2), ]
round2_post <- read_csv('~/Desktop/trainings_los/Training_Post-Survey_Round2_Pilot.csv')[-c(1, 2), ]
round2_osf <- round2_pre %>% select(RecipientEmail, osf, orcid, gscholar) %>%
  rename(osf_profile = osf, 
         orcid_profile = orcid) %>%
  mutate(osf_guid = str_extract(osf_profile, "(?<=/)[A-Za-z0-9]{5}(?=/?$)"),
         orcid = str_extract(orcid_profile, "\\d{4}-\\d{4}-\\d{4}-\\d{3}[\\dX]"))

# participant list (no-shows are possible, but they have access to the video)
## merge different institution lists to get total participant list
round2_list <- read_csv('~/Desktop/trainings_los/Round2_Algarve_email_list.csv') %>% 
  mutate(inst = 'Algarve') %>%
  bind_rows(read_csv('~/Desktop/trainings_los/Round2_Cincinnati_email_list.csv') %>% 
              mutate(inst = 'Cincinnati')) %>%
  bind_rows(read_csv('~/Desktop/trainings_los/Round2_DMS_TTT_email_list.csv') %>% 
              mutate(inst = 'DMS TTT')) %>%
  bind_rows(read_csv('~/Desktop/trainings_los/Round2_Syracuse_email_list.csv') %>% 
              mutate(inst = 'Syracuse')) %>%
  bind_rows(read_csv('~/Desktop/trainings_los/Round2_UKRN_2024_email_list.csv') %>% 
              mutate(inst = 'UKRN 2024')) %>%
  bind_rows(read_csv('~/Desktop/trainings_los/Round2_UKRN_2025_email_list.csv') %>% 
              mutate(inst = 'UKRN TTT 2025')) %>%
  bind_rows(read_csv('~/Desktop/trainings_los/Round2_UVA_Psych_2024_email_list.csv') %>% 
              mutate(inst = 'UVA Psych 2024')) %>% 
  bind_rows(read_csv('~/Desktop/trainings_los/Round2_UVA_TTT_2025_email_list.csv') %>% 
              mutate(inst = 'UVA 2025')) %>%
  bind_rows(read_csv('~/Desktop/trainings_los/Round2_VU_email_list.csv') %>% 
              mutate(inst = 'VU')) %>%
  select(-Language, -ExternalDataReference, -Phone) %>%
  # remove the 3 dups in Algarve: appear to be added later, keep latest one
  group_by(Email) %>%
  filter(CreationDate == max(CreationDate)) %>%
  ungroup() %>%
  left_join(round2_osf, by = join_by(Email == RecipientEmail)) %>%
  # only make FullName NA if both first and last are NA and don't include NA if only one name is present
  mutate(FullName = if_else(is.na(FirstName) & is.na(LastName), 
                            NA_character_, 
                            paste(FirstName, LastName, sep = " ") %>% trimws())) %>%
  left_join(dates, by = "inst")

# is_dup <- duplicated(round2_list$Email) | duplicated(round2_list$Email, fromLast = TRUE)
# dups <- round2_list[is_dup, ]
# # 3 dups in Algarve: appear to be added later

# match training participants with OSF users ----
osf_users <- read_csv("~/Desktop/nps_users_names_orcids_all.csv",
                      col_types = cols(u.deleted = col_date()))
# 1591316 users

is_dup <- duplicated(osf_users$u.username) | duplicated(osf_users$u.username, fromLast = TRUE)
dups <- osf_users[is_dup, ]
# no dups

# merge AREN and Round 2 Pilot
training_list <- aren_list %>%
  bind_rows(round2_list)
# 230 participants

write_sheet(training_list, trainings_url, sheet = "training_participants")

is_dup <- duplicated(training_list$Email) | duplicated(training_list$Email, fromLast = TRUE)
dups <- training_list[is_dup, ]
# # no dups

# priority join: GUID --> email --> ORCID --> fullname ----

## function matching ----
# see bottom for preliminary and manual matching pre-function

priority_match <- function(x, y, priorities) {
  out_list <- list()
  unmatched <- x
  
  for (i in seq_along(priorities)) {
    left_key  <- names(priorities)[i]
    right_key <- priorities[[i]]
    
    y_temp <- y
    
    # filter out NA in y for this key
    if (left_key %in% c("orcid", "FullName")) {
      y_temp <- y_temp %>% filter(!is.na(.data[[right_key]]))
    }
    
    # for FullName, keep only unique values in y
    if (left_key == "FullName") {
      y_temp <- y_temp %>% group_by(.data[[right_key]]) %>% filter(n() == 1) %>% ungroup()
    }
    
    matched <- unmatched %>%
      left_join(y_temp, by = setNames(right_key, left_key), keep = TRUE) %>%
      filter(!is.na(u._id))
    
    out_list[[i]] <- matched
    
    # update unmatched
    unmatched <- anti_join(unmatched, matched, by = names(x))
  }
  
  # combine all matched rows
  bind_rows(out_list)
}

# matched participants
osf_participants <- priority_match(
  training_list,
  osf_users,
  priorities = c(
    "osf_guid" = "u._id", 
    "Email"    = "u.username", 
    "orcid"    = "u.orcid",
    "FullName" = "u.fullname"
  )
) %>% 
  # keep only OSF database columns now that participants are matched to OSF accounts
  select(contains("u."), first_training_date, last_training_date, postsurvey_date)

# matched manual matching
# 171/230 --> 74.3% matched

is_dup <- duplicated(osf_participants$u._id) | duplicated(osf_participants$u._id, fromLast = TRUE)
dups <- osf_participants[is_dup, ]
# no dups

write_sheet(osf_participants, trainings_url, sheet = "osf_participants")

# ## prelim matching tests ----
# 
# # using osf_users (including inactive and spam users)
# 
# # email matching
# training_email <- training_list %>%
#   left_join(osf_users, by = join_by(Email == u.username))
# 
# table(is.na(training_email$u._id))
# # 134 matched
# 
# # name matching
# training_name <- training_list %>%
#   # Josiline Chigwada is a dup fullname
#   # just for prelim counts, remove users with dup fullnames
#   # need to clean this up more thoroughly in actual matching function: which one to preserve?
#   left_join(osf_users %>% distinct(u.fullname, .keep_all = TRUE) %>% filter(!is.na(u.fullname)), by = join_by(FullName == u.fullname))
# 
# table(is.na(training_name$u._id))
# # 115 matched
# 
# # GUID matching
# training_guid <- training_list %>%
#   left_join(osf_users, by = join_by(osf_guid == u._id), keep = TRUE)
# 
# table(is.na(training_guid$u._id))
# # 39 matched --> 40 GUIDs provided by participants, 1 was invalid
# 
# # ORCID matching
# training_orcid <- training_list %>%
#   left_join(osf_users %>% filter(!is.na(u.orcid)), by = join_by(orcid == u.orcid))
# 
# table(is.na(training_orcid$u._id))
# # 51 matched

# ## manual matching ----
# 
# # start with 230 participants (training_list) and match with OSF users (osf_users)
# man_guid <- training_list %>%
#   left_join(osf_users, by = join_by(osf_guid == u._id), keep = TRUE)
# # 39 matches
# 
# # among unmatched 191
# man_email <- 
#   # tryout_guid %>%
#   # filter(is.na(u._id))
#   training_list %>% anti_join(osf_users, by = join_by(osf_guid == u._id)) %>%
#   left_join(osf_users, by = join_by(Email == u.username), keep = TRUE)
# # 109 matches
# 
# # among unmatched 82
# man_orcid <- training_list %>% 
#   anti_join(osf_users, by = join_by(osf_guid == u._id)) %>%
#   anti_join(osf_users, by = join_by(Email == u.username)) %>%
#   filter(!is.na(orcid)) %>%
#   # only 12 have ORCIDs
#   left_join(osf_users, by = join_by(orcid == u.orcid), keep = TRUE)
# # 6 matches
# 
# # among unmatched 76
# man_fullname <- training_list %>%
#   anti_join(osf_users, by = join_by(osf_guid == u._id)) %>%
#   anti_join(osf_users, by = join_by(Email == u.username)) %>%
#   anti_join(osf_users %>% filter(!is.na(u.orcid)), by = join_by(orcid == u.orcid)) %>%
#   # drop duplicate fullnames
#   left_join(osf_users %>% 
#               group_by(u.fullname) %>% 
#               filter(n() == 1) %>% 
#               ungroup(), 
#             by = join_by(FullName == u.fullname), keep = TRUE)
# # 17 matches
# 
# # get total list of matched users
# man_list <- man_guid %>%
#   bind_rows(man_email, man_orcid, man_fullname) %>%
#   filter(!is.na(u._id))
# # 171 matches