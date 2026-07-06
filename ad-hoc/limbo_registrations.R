library(readr)
library(tidyverse)
library(dplyr)
library(stringr)
library(googlesheets4)
library(tibble)
library(purrr)
library(tidyr)

# all registrations
regs <- read_csv("~/Desktop/limbo_registrations_0704.csv")
# 379326

# set google sheet link (limbo_reg_url)
write_sheet(regs, limbo_reg_url, sheet = "all_regs")

# write_sheet(regs %>%
#               mutate(date_created = as.Date(date_created, tz = "UTC"),
#                      date_registered = as.Date(date_registered, tz = "UTC"),
#                      embargo_end_date = as.Date(embargo_end_date, tz = "UTC")), 
#             limbo_reg_sheet,
#             sheet = "all_regs")
# # 500: DATA_LOSS error
# # not due to POSIXct values, must be because it's too big

# non-spam, non-draft, non-pending, non-moderation rejected
limbo_regs <- regs %>%
  filter(
    (spam_status != 2 | is.na(spam_status)),
    !moderation_state %in% c(
      "pending",
      "pending_embargo_termination",
      "pending_withdraw",
      "pending_withdraw_request",
      "rejected"
    ),
    (registration_approval_state != 'moderator_rejected' |
       registration_approval_state != 'pending_moderation' |
       is.na(registration_approval_state)),
    (embargo_state != 'pending_moderation' | is.na(embargo_state)),
    (retraction_state != 'pending_moderation' | is.na(retraction_state))
  )

write_csv(limbo_regs, "~/Desktop/limbo_regs_2026-07-04.csv")

private_limbo_regs <- limbo_regs %>%
  filter(!is_public)

write_sheet(private_limbo_regs, 
            limbo_reg_url,
            sheet = "limbo_regs")
