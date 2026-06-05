library(readr)
library(tidyverse)
library(dplyr)
library(stringr)
library(googlesheets4)
library(tibble)
library(purrr)
library(tidyr)

# building Bepress subject hierarchy

# using subjects that have been selected on registrations
# some subjects may have not been selected yet, thus don't show up in the data
all_reg <- read_csv("~/Desktop/all_registrations_for_los_2026-03-04.csv")

public_reg <- all_reg %>%
  filter(is_public, !is_deleted, !is.na(date_registered), moderation_state == "accepted", (spam_status != 2 | is.na(spam_status))) %>%
  mutate(has_output = str_detect(connected_outputs, "DATA|CODE|MATERIALS|SUPPLEMENTS"),
         has_outcome = str_detect(connected_outputs, "PAPERS")) %>%
  mutate(is_los = has_output & has_outcome)

# find top-level subjects that have been selected on registrations
public_reg_subject_parent <- public_reg %>%
  mutate(subject = map(subject_parent, ~ {
    if (is.na(.x)) return(NA_character_)
    result <- fromJSON(.x)
    if (length(result) == 0) NA_character_ else as.character(result)
  })) %>%
  unnest(subject_parent) %>%
  mutate(subject_parent = if_else(is.na(subject_parent), "Unspecified", subject_parent))

view(public_reg_subject_parent %>% filter(subject == "Unspecified"))
# confirmed only one row for each reg that has "Unspecified" subject_parent

# extract top subjects -- 11 options including Unspecified
top_subjects <- public_reg_subject_parent %>%
  distinct(subject_parent)

# find lower-level subjects that have been selected on registrations
public_reg_subject <- public_reg %>%
  mutate(subject = map(subject, ~ {
    if (is.na(.x)) return(NA_character_)
    result <- fromJSON(.x)
    if (length(result) == 0) NA_character_ else as.character(result)
  })) %>%
  unnest(subject) %>%
  mutate(subject = if_else(is.na(subject), "Unspecified", subject))

# classify each lower-level subject by Bepress level depending on whether their parent subject is a top-level subject
lower_subjects <- public_reg_subject %>%
  distinct(subject) %>%
  left_join(subject_types, by = "subject") %>%
  mutate(level = case_when(!parent_subject %in% top_subjects$subject_parent ~ 3,
                           parent_subject %in% top_subjects$subject_parent ~ 2))

level_2_subjects <- lower_subjects %>%
  filter(level == 2) %>%
  rename(top_subject = parent_subject)

level_3_subjects <- lower_subjects %>%
  filter(level == 3) %>%
  left_join(level_2_subjects, by = c("parent_subject" = "subject")) %>%
  rename(level = level.x) %>%
  select(subject, top_subject, level)

lower_subject_types <- bind_rows(level_2_subjects, level_3_subjects)

# using the options in the Subject model
subject_types <- read_csv("~/Desktop/subject_types.csv")

# classify each lower-level subject by Bepress level depending on whether their parent subject is a top-level subject
lower_subjects_sm <- subject_types %>%
  filter(!subject %in% top_subjects$subject_parent) %>%
  mutate(level = case_when(!parent_subject %in% top_subjects$subject_parent ~ 3,
                           parent_subject %in% top_subjects$subject_parent ~ 2))

level_2_subjects_sm <- lower_subjects_sm %>%
  filter(level == 2) %>%
  rename(top_subject = parent_subject)

level_3_subjects_sm <- lower_subjects_sm %>%
  filter(level == 3) %>%
  left_join(level_2_subjects_sm, by = c("parent_subject" = "subject")) %>%
  rename(level = level.x) %>%
  select(subject, top_subject, level)

lower_subject_types_sm <- bind_rows(level_2_subjects_sm, level_3_subjects_sm)

# Note: questionable cases to keep an eye out on
# usually due to multiple Subject objects for a given subject text
## Law --> parent: Medieval Studies
## Neuroscience has no parent while Neurosciences does
### certain subdisciplines under Neuroscience have multiple objects in which the parent is Neuroscience OR Neurosciences

write_csv(lower_subject_types_sm, "~/Desktop/subject_types_top.csv")

# rebuild Bepress hierarchy considering subjects past level 3
## ex. Mental Health previously has no top-level subject because 4th level: 
## Mental Health > Health Psychology > Psychology > Social and Behavioral Sciences 

top_subjects <- public_reg_subject_parent %>%
  distinct(subject_parent) %>%
  pull(subject_parent)

subject_types_clean <- subject_types %>%
  mutate(parent_subject = ifelse(subject == "Law", NA, parent_subject))

subject_types_top <- subject_types_clean %>%
  select(subject, parent_subject) %>%
  distinct()

repeat {
  resolved <- subject_types_top %>%
    left_join(
      subject_types_clean %>% select(subject, parent_subject) %>%
        rename(parent_subject = subject, grandparent = parent_subject),
      by = "parent_subject"
    ) %>%
    mutate(parent_subject = ifelse(
      !is.na(grandparent) & !parent_subject %in% top_subjects,
      grandparent,
      parent_subject
    )) %>%
    select(subject, parent_subject)
  
  if (identical(resolved, subject_types_top)) break
  subject_types_top <- resolved
}

write_csv(subject_types_top %>% rename(top_subject = parent_subject), "~/Desktop/subject_types_top.csv")

# left non-top-level (parent_subject is NA) subjects alone: Areas or Regions, Earth and Life Sciences, Neuroscience, Sport and Exercise Science, Sport and Exercise Studies, Time Periods
#