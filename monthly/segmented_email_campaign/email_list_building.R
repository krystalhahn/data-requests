library(readr)
library(tidyverse)
library(dplyr)
library(stringr)
library(googlesheets4)
library(tibble)
library(purrr)
library(tidyr)
library(jsonlite)

# user-registration pairs ----
# multiple users, multiple registrations to be filtered
# to generate list of registrations and registration count per user

## compare determining age based on `created` vs `registered_date` ----
# registrations that were *created* at least 12 mo ago
# when the registered node was created
pairs_created <- read_csv("~/Desktop/user_reg_pairs_0418_created.csv")

# registrations that were *registered* at least 12 mo ago
# when the registration was created
pairs_registered <- read_csv("~/Desktop/user_reg_pairs_0418_registered.csv")

compare_dfs(pairs_created, pairs_registered, c("user_guid", "reg_guid"))
# confirmed to match

checked_pairs_age <- pairs_created %>%
  mutate(age = difftime(as.POSIXct("2026-04-18"), date_created, tz = "UTC", units = "days"))
# min(checked_pairs_age$age)
# Time difference of 365.312 days

checked_pairs_age_r <- pairs_registered %>%
  mutate(age = difftime(as.POSIXct("2026-04-18"), date_registered, tz = "UTC", units = "days"))
# min(checked_pairs_age_r$age)
# Time difference of 365.312 days
# confirmed to match

## filtering user-reg pairs to get email list ----
### public
### user has admin, read, write permission levels
### not withdrawn
### at least 12 months old
### no connected outputs (data, code, materials, supplements)

table(pairs_created$user_permissions == "['read', 'write', 'admin']")
# FALSE   TRUE 
# 281944 339371

refined_pairs <- pairs_created %>%
  filter(user_permissions == "['read', 'write', 'admin']") %>%
  filter(!str_detect(connected_resources, "DATA|ANALYTIC_CODE|MATERIALS|SUPPLEMENTS"))
# 336612 user-reg pairs

## summarize by user ----
email_list_from_pairs <- refined_pairs %>%
  group_by(user_guid, user_email) %>%
  summarize(reg_count = n(),
            reg_guids = sapply(list(reg_guid), function(x) paste(x, collapse = ", ")))
# 119230 users

# email list directly from database ----
# no wrangling necessary
email_list_direct <- read_csv("~/Desktop/email_list_0418.csv")
# 119230 users

compare_dfs(
  email_list_from_pairs %>% select(user_guid, user_email) %>% arrange(user_guid),
  email_list_direct %>% arrange(user_guid),
  "user_guid"
)
# confirmed to match

# write to sheet ----

# email_list_sheet_url <- 

write_sheet(email_list_from_pairs, email_list_sheet_url, sheet = "2026-04-18")
